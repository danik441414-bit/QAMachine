"use client";

import {
  AlertTriangle, CheckCircle2, Clock, Loader2,
  ExternalLink, FileText, Image, Code2, ChevronDown, ChevronRight,
} from "lucide-react";
import { useState } from "react";
import { cn, formatDate } from "@/lib/utils";
import { RunStatusBadge } from "@/components/ui/badge";
import type { Run, RunArtifact } from "@/types";

interface RunResultProps {
  run: Run;
}

export function RunResult({ run }: RunResultProps) {
  const [expanded, setExpanded] = useState(run.status === "completed");

  return (
    <div className="rounded-xl border border-border bg-bg overflow-hidden">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-bg-surface/50
                   transition-colors text-left"
      >
        <RunIcon status={run.status} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <RunStatusBadge status={run.status} />
            {run.mode && (
              <span className="text-2xs text-text-muted border border-border
                               rounded-full px-2 py-0.5 capitalize">
                {run.mode.replace("_", " ")}
              </span>
            )}
          </div>
          <p className="text-xs text-text-muted mt-0.5 truncate">
            {run.targetUrl}
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {run.status === "completed" && (
            <div className="flex items-center gap-3 text-2xs text-text-muted">
              <span className="flex items-center gap-1">
                <span className="text-text-secondary font-medium">{run.stepCount}</span> steps
              </span>
              {run.issueCount > 0 && (
                <SeverityPills summary={run.summary} total={run.issueCount} />
              )}
            </div>
          )}
          {expanded
            ? <ChevronDown className="h-3.5 w-3.5 text-text-muted" />
            : <ChevronRight className="h-3.5 w-3.5 text-text-muted" />}
        </div>
      </button>

      {/* ── Body ───────────────────────────────────────────────────── */}
      {expanded && (
        <div className="border-t border-border">
          {/* Running progress */}
          {run.status === "running" && (
            <div className="px-4 py-3">
              <div className="h-1 rounded-full bg-bg-elevated overflow-hidden">
                <div className="h-full w-1/2 bg-accent rounded-full animate-pulse" />
              </div>
              <p className="text-xs text-text-muted mt-2">
                Machine is testing your site…
              </p>
            </div>
          )}

          {/* Queued */}
          {run.status === "queued" && (
            <div className="px-4 py-3">
              <p className="text-xs text-text-muted">
                Task is queued. Starting soon…
              </p>
            </div>
          )}

          {/* Summary */}
          {run.summary && (
            <div className="px-4 py-3 border-b border-border">
              <p className="text-xs font-medium text-text-secondary mb-1.5">Summary</p>
              <p className="text-sm text-text-primary/90 leading-relaxed">
                {run.summary}
              </p>
            </div>
          )}

          {/* Failed */}
          {run.status === "failed" && run.errorMessage && (
            <div className="px-4 py-3 border-b border-border">
              <p className="text-xs font-medium text-error mb-1.5">Error</p>
              <p className="text-xs text-error/80 font-mono">{run.errorMessage}</p>
            </div>
          )}

          {/* Artifacts */}
          {run.artifacts.length > 0 && (
            <div className="px-4 py-3">
              <p className="text-xs font-medium text-text-secondary mb-2">Artifacts</p>
              <div className="space-y-1.5">
                {run.artifacts.map((a) => (
                  <ArtifactItem key={a.id} artifact={a} />
                ))}
              </div>
            </div>
          )}

          {/* Timestamps */}
          {(run.startedAt || run.completedAt) && (
            <div className="px-4 py-2.5 bg-bg-surface/50 border-t border-border
                            flex items-center gap-4 text-2xs text-text-muted">
              {run.startedAt && (
                <span>Started {formatDate(run.startedAt)}</span>
              )}
              {run.completedAt && (
                <span>Finished {formatDate(run.completedAt)}</span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

// ── Severity breakdown ────────────────────────────────────────────────────────

const SEV_PILLS = [
  { key: "CRITICAL", emoji: "🔴" },
  { key: "HIGH",     emoji: "🟠" },
  { key: "MEDIUM",   emoji: "🟡" },
  { key: "LOW",      emoji: "🟢" },
] as const;

function parseSeverityCounts(summary: string | null): Record<string, number> {
  const counts: Record<string, number> = {};
  if (!summary) return counts;
  for (const line of summary.split("\n")) {
    const match = line.match(/^(CRITICAL|HIGH|MEDIUM|LOW):/i);
    if (match) {
      const key = match[1].toUpperCase();
      counts[key] = (counts[key] ?? 0) + 1;
    }
  }
  return counts;
}

function SeverityPills({ summary, total }: { summary: string | null; total: number }) {
  const counts = parseSeverityCounts(summary);
  const hasCounts = Object.keys(counts).length > 0;

  if (!hasCounts) {
    return (
      <span className="text-error font-medium">{total} issues</span>
    );
  }

  return (
    <span className="flex items-center gap-1.5">
      {SEV_PILLS.map(({ key, emoji }) =>
        counts[key] ? (
          <span key={key} className="flex items-center gap-0.5">
            <span>{emoji}</span>
            <span className="font-medium text-text-secondary">{counts[key]}</span>
          </span>
        ) : null
      )}
    </span>
  );
}

function RunIcon({ status }: { status: Run["status"] }) {
  const classes = "h-4 w-4 shrink-0";
  switch (status) {
    case "queued":    return <Clock className={cn(classes, "text-text-muted")} />;
    case "running":   return <Loader2 className={cn(classes, "text-accent animate-spin")} />;
    case "completed": return <CheckCircle2 className={cn(classes, "text-success")} />;
    case "failed":    return <AlertTriangle className={cn(classes, "text-error")} />;
  }
}

const ARTIFACT_ICONS: Record<RunArtifact["type"], typeof FileText> = {
  report:          FileText,
  screenshot:      Image,
  playwright_test: Code2,
  qa_doc:          FileText,
};

const ARTIFACT_LABELS: Record<RunArtifact["type"], string> = {
  report:          "QA Report",
  screenshot:      "Screenshot",
  playwright_test: "Playwright Test",
  qa_doc:          "QA Document",
};

function ArtifactItem({ artifact }: { artifact: RunArtifact }) {
  const Icon = ARTIFACT_ICONS[artifact.type];

  async function handleDownload(e: React.MouseEvent) {
    e.preventDefault();
    try {
      const token = typeof window !== "undefined"
        ? localStorage.getItem("access_token")
        : null;
      const url = `/api/v1/runs/artifact?artifact_id=${artifact.id}&token=${token ?? ""}`;
      const response = await fetch(url);
      if (!response.ok) throw new Error("Download failed");
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objectUrl;
      a.download = artifact.name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(objectUrl);
    } catch {
      alert("Failed to download file");
    }
  }

  return (
    <button
      onClick={handleDownload}
      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg bg-bg-surface
                 hover:bg-bg-elevated border border-border hover:border-border-focus
                 transition-all group text-left"
    >
      <Icon className="h-3.5 w-3.5 text-text-muted shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-xs text-text-primary truncate">{artifact.name}</p>
        <p className="text-2xs text-text-muted">{ARTIFACT_LABELS[artifact.type]}</p>
      </div>
      <ExternalLink
        className="h-3 w-3 text-text-muted opacity-0 group-hover:opacity-100 shrink-0
                   transition-opacity"
      />
    </button>
  );
}
