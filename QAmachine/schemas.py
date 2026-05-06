from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TestMode(str, Enum):
    SMOKE = "smoke"
    STANDARD = "standard"
    DEEP = "deep"


# ── Top-level intent (what the user actually wants) ────────────────────────────

class Intent(str, Enum):
    BROWSER_TEST       = "browser_test"       # standard in-browser QA session
    MOBILE_TEST        = "mobile_test"        # mobile-emulated QA session
    GENERATE_DOCS      = "generate_docs"      # test cases / checklist / test plan
    GENERATE_AUTOMATION = "generate_automation"  # playwright .py test file
    COMPARE_ENVS       = "compare_envs"       # staging vs production diff


class DocType(str, Enum):
    TEST_CASES = "test_cases"
    CHECKLIST  = "checklist"
    TEST_PLAN  = "test_plan"


class AutomationTestType(str, Enum):
    SMOKE       = "smoke"
    FUNCTIONAL  = "functional"
    REGRESSION  = "regression"
    MOBILE      = "mobile"


# ── Mobile emulation config ────────────────────────────────────────────────────

class MobileConfig(BaseModel):
    device_name:         str   = "iPhone 12"
    viewport_width:      int   = 390
    viewport_height:     int   = 844
    user_agent:          str   = ""
    is_mobile:           bool  = True
    has_touch:           bool  = True
    device_scale_factor: float = 3.0


# ── Intent parser output ───────────────────────────────────────────────────────

class IntentResult(BaseModel):
    intent: Intent = Field(description="What the user wants to do")
    doc_type: Optional[DocType] = Field(
        default=None,
        description="For GENERATE_DOCS: which document type to produce"
    )
    automation_test_type: Optional[AutomationTestType] = Field(
        default=None,
        description="For GENERATE_AUTOMATION: what test style to generate"
    )
    test_scope: str = Field(
        default="",
        description="Specific section/feature/page the user is targeting. Empty = full site."
    )
    scope_url_keywords: list[str] = Field(
        default_factory=list,
        description="URL path fragments that indicate we are inside the test scope"
    )
    scope_entry_steps: list[str] = Field(
        default_factory=list,
        description="Steps to navigate from homepage to the target scope"
    )
    device_name: str = Field(
        default="iPhone 12",
        description="For MOBILE_TEST: device to emulate"
    )
    mobile_check_type: str = Field(
        default="functional",
        description="For MOBILE_TEST: what kind of check — ui_ux / functional / regression"
    )
    credentials_text: str = Field(
        default="",
        description="Login credentials extracted from the task, if any"
    )
    changed_areas: list[str] = Field(
        default_factory=list,
        description="For regression: areas the user says were recently changed"
    )
    comparison_url: str = Field(
        default="",
        description="For COMPARE_ENVS: the second URL to compare against (e.g. staging URL)"
    )


class PageType(str, Enum):
    LANDING = "landing"
    AUTH = "auth"
    DASHBOARD = "dashboard"
    LIST = "list"
    DETAIL = "detail"
    FORM = "form"
    CHECKOUT = "checkout"
    SETTINGS = "settings"
    ERROR = "error"
    UNKNOWN = "unknown"


class NavAction(str, Enum):
    CLICK = "click"
    TYPE = "type"
    GO_TO_MAIN = "go_to_main"
    PRESS_KEY = "press_key"
    SCROLL_DOWN = "scroll_down"
    DONE = "done"
    HOVER = "hover"              # reveal tooltip / hover-menu; check hover states
    SELECT = "select"            # pick option from <select>; value_to_type = option text
    DOUBLE_CLICK = "double_click"  # activate cell editor / expand widget


class SessionMode(str, Enum):
    UI_UX = "ui_ux"                          # Visual/layout/design issues only
    FUNCTIONAL = "functional"                # Feature behavior only
    SPECIFIC_FLOW = "specific_flow"          # Exact flow from user prompt
    ALL_FLOWS = "all_flows"                  # Discover all flows → positive → negative
    REGRESSION = "regression"               # Changed areas + neighboring zones
    NETWORK = "network"                     # Network errors, 4xx/5xx, slow requests
    API = "api"                             # Collect + test API endpoints
    LOAD_PERFORMANCE = "load_performance"   # Page load times, slow resources
    MOBILE = "mobile"                       # Mobile device emulation + mobile-specific checks
    ACCESSIBILITY = "accessibility"         # WCAG 2.1 AA audit via axe-core injection


# ── Planner output ─────────────────────────────────────────────────────────────

class TestMission(BaseModel):
    session_mode: SessionMode = Field(
        description="Testing mode detected from the user task"
    )
    coverage_targets: list[str] = Field(
        description="Sections/features/flows the agent MUST cover"
    )
    strategy_notes: str = Field(
        description="How to explore: order, depth, what to focus on, positive vs negative phases"
    )
    stop_conditions: list[str] = Field(
        description="Conditions that trigger early termination, e.g. 'all nav items visited'"
    )
    allow_typing: bool = Field(
        description="Whether the agent may fill text inputs"
    )
    credentials_text: str = Field(
        default="",
        description="Login credentials extracted from the task as plain text, e.g. 'username: admin, password: pass123'. Empty if not needed."
    )
    user_flows: list[str] = Field(
        default_factory=list,
        description=(
            "SPECIFIC_FLOW: ordered steps of the exact flow to execute. "
            "ALL_FLOWS: list of flows to test, each annotated with POSITIVE or NEGATIVE phase. "
            "Empty for other modes."
        )
    )
    test_scope: str = Field(
        default="",
        description=(
            "Specific area to restrict testing to (e.g. 'account section', 'checkout', 'search form'). "
            "Empty means full site. Used when user asks to test only a specific part."
        )
    )
    scope_entry_steps: list[str] = Field(
        default_factory=list,
        description=(
            "Minimal navigation steps to REACH the test scope from the homepage. "
            "e.g. ['click Login', 'navigate to My Account']. Empty if scope is reachable directly."
        )
    )
    changed_areas: list[str] = Field(
        default_factory=list,
        description=(
            "REGRESSION only: list of areas/features the user says were recently changed. "
            "e.g. ['cart', 'checkout flow', 'user profile']. Empty for other modes."
        )
    )
    recommended_max_steps: int = Field(
        default=35,
        description=(
            "How many steps to budget for this session. "
            "Narrow scope = 15-25. Medium scope = 25-40. Full site = 40-60. Deep audit = 80-100. "
            "LOAD_PERFORMANCE = 20. API = 30. SPECIFIC_FLOW = 20."
        )
    )
    scope_url_keywords: list[str] = Field(
        default_factory=list,
        description=(
            "URL path keywords that indicate the browser is inside the test scope. "
            "e.g. for 'account section': ['/account', '/profile', '/user', '/settings']. "
            "Empty list = no URL restriction (full site). "
            "Used by the orchestrator to detect scope drift and trigger re-entry."
        )
    )
    mobile_config: Optional[MobileConfig] = Field(
        default=None,
        description=(
            "Mobile emulation config. Set for MOBILE session mode. "
            "Orchestrator uses this to configure the Playwright browser context."
        )
    )


# ── Per-step context ───────────────────────────────────────────────────────────

class DOMElement(BaseModel):
    id: str
    tag: str
    text: str


class PageContext(BaseModel):
    step: int
    current_url: str
    page_type: Optional[PageType] = None
    dom_elements: list[DOMElement]
    aria_snapshot: str
    console_errors: list[str]
    network_errors: list[str] = Field(default_factory=list)   # 4xx/5xx from network capture
    page_load_ms: int = 0                                      # page load duration in ms
    screenshot_b64: str
    url_stay_count: int
    visited_urls: list[str]
    clicked_element_ids: list[str]
    nav_items_clicked: list[str]
    action_history: list[str]
    mission: TestMission
    uncovered_targets: list[str] = Field(default_factory=list)
    user_task: str = ""   # the user's original literal request — always visible to explorer


# ── Explorer output ────────────────────────────────────────────────────────────

class IssueHypothesis(BaseModel):
    description: str = Field(description="One-sentence description of the suspected defect")
    element_id: Optional[str] = Field(default=None, description="qa-id of the element involved, if any")
    confidence: float = Field(ge=0.0, le=1.0, description="0..1 confidence that this is a real bug")


class NavigationDecision(BaseModel):
    visual_summary: str = Field(description="Brief description of what is currently visible on screen")
    page_type: PageType = Field(description="Classification of the current page type")
    reasoning: str = Field(description="Why this action advances the mission")
    action: NavAction
    target_id: str = Field(
        default="",
        description="qa-id digit from DOM list. Required for click/type/hover/select/double_click. Empty for go_to_main/press_key/scroll_down/done."
    )
    value_to_type: str = Field(
        default="",
        description="Text to type if action==type. Option text to choose if action==select. Empty for other actions."
    )
    suspected_issues: list[IssueHypothesis] = Field(
        default_factory=list,
        description="Suspected UI/UX issues spotted on this screen with confidence scores"
    )


# ── Judge output ───────────────────────────────────────────────────────────────

class VerifiedIssue(BaseModel):
    description: str
    severity: str = Field(description="critical / high / medium / low")
    url: str
    step: int
    element_id: Optional[str] = None
    evidence: str = Field(description="Quote from DOM/aria/console confirming the bug")
    screenshot_path: str = ""


# ── Step log ───────────────────────────────────────────────────────────────────

class StepLog(BaseModel):
    step: int
    url: str
    action: str
    target_id: str
    target_text: str
    reasoning: str
    suspected_issues: list[IssueHypothesis]
    verified_issues: list[VerifiedIssue]
    screenshot_path: str
