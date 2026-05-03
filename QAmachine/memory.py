from __future__ import annotations
from collections import Counter
from dataclasses import dataclass, field
from urllib.parse import urlparse

from schemas import DOMElement, StepLog, VerifiedIssue

# How many times the same button text can be clicked globally before being suppressed
_MAX_SAME_BUTTON_CLICKS = 3


@dataclass
class CoverageTracker:
    """Tracks what has been visited and interacted with during the session."""

    visited_urls: set[str] = field(default_factory=set)
    url_stay_count: int = 0
    _last_path: str = ""

    # Cleared on every URL change
    clicked_element_ids: set[str] = field(default_factory=set)

    # Persists across URLs — prevents re-clicking the same nav links
    nav_items_clicked: set[str] = field(default_factory=set)

    # Global counter: how many times each button text was clicked (survives URL changes)
    _button_click_counts: Counter = field(default_factory=Counter)

    def on_navigation(self, url: str) -> None:
        """Call at the start of each step with the current page URL."""
        path = urlparse(url).path
        self.visited_urls.add(url)
        if path == self._last_path:
            self.url_stay_count += 1
        else:
            self.url_stay_count = 0
            self._last_path = path
            self.clicked_element_ids.clear()

    def record_click(self, element_id: str, element_text: str, is_nav: bool = False) -> None:
        self.clicked_element_ids.add(element_id)
        normalized = element_text.strip().lower()
        if normalized:
            self._button_click_counts[normalized] += 1
        if is_nav and normalized:
            self.nav_items_clicked.add(normalized)

    def reset_to_main(self, _main_url: str) -> None:
        """Call after a go_to_main action."""
        self.url_stay_count = 0
        self._last_path = ""
        self.clicked_element_ids.clear()

    def available_elements(self, dom: list[DOMElement]) -> list[DOMElement]:
        """
        Filter DOM to elements not yet interacted with on the current URL.

        Filtering order:
        1. Skip elements whose id is already in clicked_element_ids.
        2. Skip <a> links whose normalized text is already in nav_items_clicked.
        3. Skip buttons/links whose text has been clicked >= _MAX_SAME_BUTTON_CLICKS times.
        4. Cap at 200 to stay within LLM context budget.
        """
        result = []
        for el in dom:
            # Input/textarea fields are always re-available — they can be re-filled
            if el.tag not in ("input", "textarea") and el.id in self.clicked_element_ids:
                continue
            normalized = el.text.strip().lower()
            if el.tag == "a" and normalized in self.nav_items_clicked:
                continue
            if normalized and self._button_click_counts[normalized] >= _MAX_SAME_BUTTON_CLICKS:
                continue
            result.append(el)
        return result[:200]

    @property
    def is_stuck(self) -> bool:
        return self.url_stay_count >= 5

    def snapshot(self) -> dict:
        """Return a serializable snapshot for passing into PageContext."""
        # Show buttons clicked 2+ times so explorer knows what's looping
        repeated = [t for t, c in self._button_click_counts.items() if c >= 2]
        return {
            "url_stay_count": self.url_stay_count,
            "visited_urls": self.visited_urls,
            "clicked_element_ids": self.clicked_element_ids,
            "nav_items_clicked": self.nav_items_clicked,
            "repeated_button_texts": repeated,
        }


@dataclass
class SemanticLog:
    """Append-only record of steps, issues, and screenshot paths for the final report."""

    steps: list[StepLog] = field(default_factory=list)
    verified_issues: list[VerifiedIssue] = field(default_factory=list)
    journey_screenshots: list[str] = field(default_factory=list)

    # NETWORK mode: accumulated failed/slow requests across the whole session
    network_events: list[dict] = field(default_factory=list)

    # API mode: unique API endpoints observed {url: {method, status, resource_type}}
    api_endpoints: dict = field(default_factory=dict)

    # API mode: test results after session [{url, method, status, duration_ms, error}]
    api_results: list[dict] = field(default_factory=list)

    # LOAD_PERFORMANCE mode: page timing per navigation [{url, step, load_ms, dom_ms}]
    perf_metrics: list[dict] = field(default_factory=list)

    # LOAD_PERFORMANCE mode: repeated-request results [{url, passes, avg_ms, min_ms, max_ms, errors}]
    load_test_results: list[dict] = field(default_factory=list)

    def add_step(self, step: StepLog) -> None:
        self.steps.append(step)
        self.verified_issues.extend(step.verified_issues)
        if step.screenshot_path:
            self.journey_screenshots.append(step.screenshot_path)

    def last_n_actions(self, n: int = 10) -> list[str]:
        lines = []
        for s in self.steps[-n:]:
            path = urlparse(s.url).path or "/"
            lines.append(
                f"Step {s.step} [{path}]: {s.action} -> '{s.target_text}' | {s.reasoning[:80]}"
            )
        return lines
