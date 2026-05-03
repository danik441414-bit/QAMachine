"""
DOCX Report Writer — generates a Word document from QA session results.

For each confirmed bug:
  - Severity badge (coloured heading)
  - Description, URL, Step, Evidence
  - Screenshot embedded inline (if file exists)

Usage:
  from docx_writer import write_docx
  docx_path = write_docx(
      md_path="reports/qa_reports/QA_Report_xxx.md",
      mission=mission,
      target_url=target_url,
      user_task=user_task,
      verified_issues=log.verified_issues,
      steps=log.steps,
  )
"""
from __future__ import annotations

import datetime
import os
from typing import TYPE_CHECKING

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

if TYPE_CHECKING:
    from schemas import VerifiedIssue, StepLog, TestMission

# ── Severity colours ──────────────────────────────────────────────────────────

_SEV_COLOR = {
    "critical": RGBColor(0xC0, 0x00, 0x00),   # dark red
    "high":     RGBColor(0xFF, 0x66, 0x00),   # orange
    "medium":   RGBColor(0xFF, 0xBB, 0x00),   # amber
    "low":      RGBColor(0x00, 0x80, 0x00),   # green
}
_SEV_LABEL = {
    "critical": "🔴 CRITICAL",
    "high":     "🟠 HIGH",
    "medium":   "🟡 MEDIUM",
    "low":      "🟢 LOW",
}
_SEV_ORDER = ["critical", "high", "medium", "low"]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _set_cell_bg(cell, hex_color: str) -> None:
    """Set cell background colour via raw XML."""
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  hex_color)
    tcPr.append(shd)


def _add_metadata_table(doc: Document, rows: list[tuple[str, str]]) -> None:
    table = doc.add_table(rows=len(rows), cols=2)
    table.style = "Table Grid"
    for i, (key, val) in enumerate(rows):
        row = table.rows[i]
        row.cells[0].text = key
        row.cells[0].paragraphs[0].runs[0].bold = True
        row.cells[1].text = val
        _set_cell_bg(row.cells[0], "F2F2F2")


def _add_sev_heading(doc: Document, sev: str, count: int) -> None:
    p = doc.add_heading(f"{_SEV_LABEL[sev]}  ({count})", level=2)
    for run in p.runs:
        run.font.color.rgb = _SEV_COLOR.get(sev, RGBColor(0, 0, 0))


def _add_issue(doc: Document, idx: int, issue: "VerifiedIssue") -> None:
    """Render one bug entry: metadata + screenshot."""
    # Bug title
    p = doc.add_paragraph()
    run = p.add_run(f"{idx}. {issue.description}")
    run.bold = True
    run.font.size = Pt(11)

    # Metadata table
    meta_rows = [
        ("URL",      issue.url or "—"),
        ("Step",     str(issue.step)),
        ("Element",  issue.element_id or "N/A"),
        ("Evidence", issue.evidence or "—"),
    ]
    tbl = doc.add_table(rows=len(meta_rows), cols=2)
    tbl.style = "Table Grid"
    for i, (key, val) in enumerate(meta_rows):
        row = tbl.rows[i]
        row.cells[0].text = key
        row.cells[0].paragraphs[0].runs[0].bold = True
        _set_cell_bg(row.cells[0], "F5F5F5")
        row.cells[1].text = val
        # Make evidence cell italic
        if key == "Evidence":
            for run in row.cells[1].paragraphs[0].runs:
                run.italic = True

    # Screenshot — resolve relative paths from QAmachine working dir
    screenshot_path = issue.screenshot_path or ""
    if screenshot_path and not os.path.isabs(screenshot_path):
        # Try relative to CWD first, then relative to QAmachine root
        qamachine_root = os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(qamachine_root, screenshot_path)
        if os.path.exists(candidate):
            screenshot_path = candidate
    if screenshot_path and os.path.exists(screenshot_path):
        doc.add_paragraph()   # small gap
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run_img = p_img.add_run()
        try:
            run_img.add_picture(screenshot_path, width=Inches(5.5))
        except Exception:
            p_img.add_run(f"[Screenshot: {screenshot_path}]").italic = True
    else:
        p_no = doc.add_paragraph(f"Screenshot: {screenshot_path or 'not available'}")
        p_no.runs[0].italic = True
        p_no.runs[0].font.color.rgb = RGBColor(0x99, 0x99, 0x99)

    doc.add_paragraph()   # spacing after issue


# ── Public API ─────────────────────────────────────────────────────────────────

def write_docx(
    md_path: str,
    mission: "TestMission",
    target_url: str,
    user_task: str,
    verified_issues: list["VerifiedIssue"],
    steps: list["StepLog"],
) -> str:
    """
    Generate a .docx report alongside the existing .md report.
    Returns the path to the saved .docx file.
    """
    doc = Document()

    # ── Page margins (narrower for more content width) ────────────────────────
    for section in doc.sections:
        section.top_margin    = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin   = Inches(1.0)
        section.right_margin  = Inches(1.0)

    # ── Title ─────────────────────────────────────────────────────────────────
    title = doc.add_heading("QAmachine QA Report", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    ts         = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mode_label = mission.session_mode.value.replace("_", " ").title()
    scope_note = mission.test_scope or "Full site"

    _add_metadata_table(doc, [
        ("Target",           target_url),
        ("Task",             user_task),
        ("Mode",             mode_label),
        ("Scope",            scope_note),
        ("Generated",        ts),
        ("Steps",            f"{len(steps)} / {mission.recommended_max_steps} budget"),
        ("Confirmed issues", str(len(verified_issues))),
    ])

    doc.add_paragraph()

    # ── Summary by severity ───────────────────────────────────────────────────
    doc.add_heading("Issue Summary", level=1)
    by_sev: dict[str, list["VerifiedIssue"]] = {s: [] for s in _SEV_ORDER}
    for issue in verified_issues:
        by_sev.setdefault(issue.severity.lower(), []).append(issue)

    tbl = doc.add_table(rows=1, cols=2)
    tbl.style = "Table Grid"
    hdr = tbl.rows[0]
    hdr.cells[0].text = "Severity"
    hdr.cells[1].text = "Count"
    for cell in hdr.cells:
        cell.paragraphs[0].runs[0].bold = True
        _set_cell_bg(cell, "D9D9D9")
    for sev in _SEV_ORDER:
        count = len(by_sev[sev])
        if count == 0:
            continue
        row = tbl.add_row()
        row.cells[0].text = _SEV_LABEL[sev]
        row.cells[1].text = str(count)

    doc.add_paragraph()

    # ── Confirmed Issues ──────────────────────────────────────────────────────
    doc.add_heading("Confirmed Issues", level=1)

    if not verified_issues:
        doc.add_paragraph("No defects confirmed during this session.")
    else:
        for sev in _SEV_ORDER:
            issues = by_sev.get(sev, [])
            if not issues:
                continue
            _add_sev_heading(doc, sev, len(issues))
            for i, issue in enumerate(issues, 1):
                _add_issue(doc, i, issue)

    # ── Action Log (compact) ──────────────────────────────────────────────────
    doc.add_page_break()
    doc.add_heading("Action Log", level=1)
    for step in steps:
        bug_note = ""
        if step.verified_issues:
            bug_note = "  BUG: " + "; ".join(vi.description[:60] for vi in step.verified_issues)
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(f"Step {step.step}").bold = True
        p.add_run(f"  {step.action} → {step.target_text or '—'}  |  {step.reasoning[:80]}")
        if bug_note:
            p.add_run(bug_note).font.color.rgb = RGBColor(0xC0, 0x00, 0x00)

    # ── Save ──────────────────────────────────────────────────────────────────
    docx_path = md_path.replace(".md", ".docx")
    doc.save(docx_path)
    return docx_path
