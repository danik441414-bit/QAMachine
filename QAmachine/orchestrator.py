from __future__ import annotations
import asyncio
import base64
import concurrent.futures
import datetime
import logging
import os
import shutil
import traceback
from urllib.parse import urlparse

log = logging.getLogger(__name__)

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from schemas import (
    TestMode, TestMission, PageContext, NavigationDecision,
    NavAction, StepLog, VerifiedIssue, SessionMode, PageType,
)
from memory import CoverageTracker, SemanticLog
from context_builder import build_page_context
from agents import planner, explorer, judge, reporter
from agents import api_tester

TRACES_DIR  = "ux_traces"
REPORTS_DIR = os.path.join("reports", "qa_reports")

# Fallback step budgets when no pre-built mission is provided (legacy mode)
_MODE_STEPS = {TestMode.SMOKE: 15, TestMode.STANDARD: 35, TestMode.DEEP: 100}

# How many consecutive steps outside scope before we force re-entry
_SCOPE_DRIFT_THRESHOLD = 2


class Orchestrator:
    """
    Coordinates the full QA session.

    Accepts either:
      - mission=<TestMission>   — pre-built mission from planner (recommended, used by main.py)
      - mode=<TestMode>         — legacy depth selector; planner is called inside run()

    Per-step pipeline:
      1. on_navigation()       — update coverage tracker
      2. _check_scope_drift()  — detect if we wandered outside the test scope
      3. build_page_context()  — screenshot + DOM + aria + network events
      4. available_elements()  — filter DOM for Explorer
      5. explorer.decide()     — NavigationDecision (1 LLM call)
      6. _run_judge()          — parallel verification of hypotheses
      7. _execute()            — Playwright action
      8. log_step()            — append to SemanticLog

    Post-session:
      - API mode: test collected endpoints with api_tester
      - LOAD_PERFORMANCE mode: repeat-test slow endpoints for accurate timing
    """

    def __init__(
        self,
        target_url: str,
        user_task: str,
        mode: TestMode = TestMode.STANDARD,
        mission: TestMission | None = None,
        headless: bool = False,
    ):
        self.target_url  = target_url
        self.user_task   = user_task
        self.base_domain = urlparse(target_url).netloc.replace("www.", "")

        # Accept pre-built mission (from main.py) or build it lazily inside run()
        self.mission: TestMission | None = mission

        # Step budget: will be overwritten from mission after planning
        self._fallback_steps = _MODE_STEPS[mode]
        self.max_steps = mission.recommended_max_steps if mission else self._fallback_steps

        self.headless = headless
        self.tracker = CoverageTracker()
        self.log     = SemanticLog()

        # Scope drift tracking
        self._scope_drift_count = 0

        # Early-exit: consecutive forced go_to_main with no valid elements
        self._no_elements_streak = 0

        # Circuit breaker: consecutive go_to_main regardless of available elements
        self._go_to_main_streak = 0

        # Failure detection
        self.failure_reason: str = ""       # Human-readable reason if session stopped early
        self._credentials_typed = False     # True after agent types into an auth form
        self._login_error_streak = 0        # Consecutive steps showing login error
        self._auth_wall_streak = 0          # Consecutive steps showing auth wall

        # Console / network buffers
        self._console_errors: list[str] = []
        self._network_buffer: list[dict] = []   # raw per-step, drained each step

    # ── Public entry point ─────────────────────────────────────────────────────

    async def run(self) -> str:
        """Run the full session. Returns the path to the generated report file."""
        if os.path.exists(TRACES_DIR):
            shutil.rmtree(TRACES_DIR)
        os.makedirs(TRACES_DIR, exist_ok=True)

        # Plan only if not pre-built
        if self.mission is None:
            print("Planning mission...")
            self.mission = planner.create_mission(
                self.user_task, self.target_url, self._fallback_steps
            )
            self.max_steps = self.mission.recommended_max_steps

        mode_label = self.mission.session_mode.value.upper()
        scope_note = f" | Scope: {self.mission.test_scope}" if self.mission.test_scope else ""
        kw_note    = (
            f" [{', '.join(self.mission.scope_url_keywords[:3])}]"
            if self.mission.scope_url_keywords else ""
        )
        print(f"Mode   : {mode_label}{scope_note}{kw_note}")
        print(f"Steps  : {self.max_steps}")
        print(f"Targets: {', '.join(self.mission.coverage_targets)}")
        if self.mission.changed_areas:
            print(f"Changed: {', '.join(self.mission.changed_areas)}")

        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(headless=self.headless)

            mc = self.mission.mobile_config if self.mission else None
            context: BrowserContext
            if mc:
                context = await browser.new_context(
                    viewport={"width": mc.viewport_width, "height": mc.viewport_height},
                    user_agent=mc.user_agent or None,
                    is_mobile=mc.is_mobile,
                    has_touch=mc.has_touch,
                    device_scale_factor=mc.device_scale_factor,
                )
                print(f"Device : {mc.device_name} ({mc.viewport_width}x{mc.viewport_height})")
            else:
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 720}
                )

            page: Page = await context.new_page()

            # Listeners
            page.on("console",   self._on_console)
            page.on("pageerror", lambda err: self._console_errors.append(str(err)))
            page.on("response",  self._on_response)   # network capture

            try:
                print(f"Navigating to {self.target_url}...")
                await page.goto(self.target_url, wait_until="domcontentloaded", timeout=60_000)
                await self._main_loop(page)
            except KeyboardInterrupt:
                print("\nSession interrupted.")
            except Exception as e:
                print(f"\nFatal session error: {e}")
                traceback.print_exc()
            finally:
                await browser.close()

        # Post-session: API testing phase
        if self.mission.session_mode == SessionMode.API and self.log.api_endpoints:
            print(f"\nRunning API tests on {len(self.log.api_endpoints)} collected endpoints...")
            self.log.api_results = api_tester.run(self.log.api_endpoints)
            print(f"API tests done: {len(self.log.api_results)} results.")

        # Post-session: LOAD_PERFORMANCE — repeat slowest endpoints
        if self.mission.session_mode == SessionMode.LOAD_PERFORMANCE and self.log.api_endpoints:
            slow_urls = self._pick_slow_endpoints()
            if slow_urls:
                print(f"\nLoad-testing {len(slow_urls)} key endpoint(s) (3 passes each)...")
                self.log.load_test_results = api_tester.load_test(slow_urls, passes=3)
                print(f"Load test done.")

        return self._write_report()

    # ── Listeners ──────────────────────────────────────────────────────────────

    def _on_console(self, msg) -> None:
        if msg.type == "error":
            self._console_errors.append(msg.text)

    def _on_response(self, response) -> None:
        """Sync Playwright response listener — collects network events."""
        try:
            req = response.request
            entry = {
                "url":           response.url,
                "method":        req.method,
                "status":        response.status,
                "resource_type": req.resource_type,
            }
            self._network_buffer.append(entry)
            self.log.network_events.append(entry)   # session-wide log

            # Collect unique API endpoints (XHR / fetch) for API / LOAD modes
            if req.resource_type in ("xhr", "fetch"):
                url_key = response.url.split("?")[0]   # strip query params for dedup
                if url_key not in self.log.api_endpoints:
                    self.log.api_endpoints[url_key] = {
                        "url":    response.url,
                        "method": req.method,
                        "status": response.status,
                    }
        except Exception:
            pass

    def _drain_console(self) -> list[str]:
        errors = list(self._console_errors[-20:])
        self._console_errors.clear()
        return errors

    def _drain_network(self) -> list[dict]:
        events = list(self._network_buffer)
        self._network_buffer.clear()
        return events

    # ── Scope drift guard ──────────────────────────────────────────────────────

    def _is_in_scope(self, url: str) -> bool:
        """Return True if the current URL is within the mission's test scope.
        Always True when no scope URL keywords are defined (full-site test).
        """
        keywords = self.mission.scope_url_keywords if self.mission else []
        if not keywords:
            return True
        url_lower = url.lower()
        return any(kw.lower() in url_lower for kw in keywords)

    def _check_scope_drift(self, page: Page) -> bool:
        """Returns True and prints a warning if we have drifted outside scope too long."""
        if not (self.mission and self.mission.scope_url_keywords):
            return False

        if self._is_in_scope(page.url):
            self._scope_drift_count = 0
            return False

        self._scope_drift_count += 1
        if self._scope_drift_count >= _SCOPE_DRIFT_THRESHOLD:
            print(
                f"  [SCOPE DRIFT x{self._scope_drift_count}] "
                f"Outside '{self.mission.test_scope}' — URL: {page.url[:70]}"
            )
            return True
        return False

    # ── Slow endpoint picker for LOAD_PERFORMANCE ──────────────────────────────

    def _pick_slow_endpoints(self) -> list[str]:
        """Select the top 5 slowest / error-prone endpoints seen in perf_metrics."""
        seen: set[str] = set()
        candidates: list[tuple[int, str]] = []

        for p in self.log.perf_metrics:
            url = p.get("url", "")
            load = p.get("load_ms", 0)
            if url and url not in seen:
                seen.add(url)
                candidates.append((load, url))

        # Also include API endpoints that had 4xx/5xx
        for key, info in self.log.api_endpoints.items():
            url = info.get("url", key)
            if url not in seen and info.get("status", 0) >= 400:
                seen.add(url)
                candidates.append((9999, url))

        candidates.sort(key=lambda x: -x[0])
        return [url for _, url in candidates[:5]]

    # ── Hard blocker detection ─────────────────────────────────────────────────

    async def _detect_hard_blocker(self, page: Page, step: int) -> bool:
        """
        Detect critical blockers that prevent testing from continuing.
        Returns True and sets self.failure_reason if a blocker is found.
        Only runs from step 2 onwards to let the agent navigate first.
        """
        if step < 2:
            return False
        try:
            pd = await page.evaluate("""() => ({
                text:  (document.body?.innerText ?? '').toLowerCase().slice(0, 3000),
                title: (document.title ?? '').toLowerCase(),
            })""")
            text  = pd.get("text", "")
            title = pd.get("title", "")
        except Exception:
            return False

        # 1. CAPTCHA
        if any(s in text for s in [
            "verify you are human", "i'm not a robot", "complete the captcha",
            "are you a robot", "prove you are human", "hcaptcha", "recaptcha",
        ]):
            self.failure_reason = (
                "CAPTCHA detected. The site is asking for human verification "
                "which an automated agent cannot complete. "
                "Tip: try a site without bot protection, or use a session cookie."
            )
            return True

        # 2. Cloudflare / DDoS shield
        if ("just a moment" in title or ("cloudflare" in text and (
            "checking your browser" in text or "enable javascript and cookies" in text
        ))):
            self.failure_reason = (
                "Bot protection (Cloudflare) detected. The site blocked automated testing. "
                "Tip: Cloudflare shields prevent browser automation — this site cannot be tested this way."
            )
            return True

        # 3. Auth wall — login required, no credentials provided
        auth_wall_signals = [
            "please log in", "please sign in", "login to continue",
            "sign in to continue", "you must be logged in",
            "login required", "authentication required", "must be authenticated",
            "пожалуйста войдите", "необходима авторизация", "требуется вход",
        ]
        if not self.mission.credentials_text and any(s in text for s in auth_wall_signals):
            self._auth_wall_streak += 1
            if self._auth_wall_streak >= 3:
                self.failure_reason = (
                    "Login required. The site requires authentication to access content, "
                    "but no credentials were provided. "
                    "Tip: add your credentials to the task, e.g.: "
                    "'Test the site. Login: user@example.com, Password: mypass'"
                )
                return True
        else:
            self._auth_wall_streak = 0

        # 4. Login failure after credentials were submitted
        if self._credentials_typed:
            login_errors = [
                "invalid credentials", "wrong password", "incorrect password",
                "invalid email", "login failed", "authentication failed",
                "invalid username", "account not found", "password incorrect",
                "неверный пароль", "неверный логин", "неверные данные",
                "ошибка входа", "неправильный пароль",
            ]
            if any(s in text for s in login_errors):
                self._login_error_streak += 1
                if self._login_error_streak >= 2:
                    self.failure_reason = (
                        "Login failed. The provided credentials were rejected by the site. "
                        "Tip: check that your login and password are correct and try again."
                    )
                    return True
            else:
                self._login_error_streak = 0

        # 5. Critical server errors
        if any(s in text for s in [
            "502 bad gateway", "503 service unavailable",
            "500 internal server error", "504 gateway timeout",
        ]):
            self.failure_reason = (
                "Site error detected. The website is returning server errors (5xx). "
                "Tip: the site may be temporarily down — try again later."
            )
            return True

        return False

    # ── Main loop ──────────────────────────────────────────────────────────────

    async def _main_loop(self, page: Page) -> None:
        for step in range(1, self.max_steps + 1):

            # Domain guard
            current_domain = urlparse(page.url).netloc.replace("www.", "")
            if self.base_domain not in current_domain:
                print(f"  Domain escape ({current_domain}), returning to home.")
                await page.goto(self.target_url, wait_until="domcontentloaded", timeout=60_000)
                await page.wait_for_timeout(1500)

            # Page stability — wait for SPA to render (Vue/React apps need longer)
            await page.wait_for_timeout(1500)
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            # Extra check: wait for body to have visible content (SPA guard)
            try:
                await page.wait_for_function(
                    "document.body && document.body.innerText.trim().length > 50",
                    timeout=5000,
                )
            except Exception:
                pass
            await page.wait_for_timeout(500)

            # 1. Hard blocker check (CAPTCHA, auth wall, bot protection, site error)
            if await self._detect_hard_blocker(page, step):
                print(f"\n  [BLOCKED] {self.failure_reason[:120]}")
                break

            # 2. Coverage tracker
            self.tracker.on_navigation(page.url)

            # 3. Scope drift detection
            scope_drifted = self._check_scope_drift(page)
            if scope_drifted:
                # Force return to main, then let the LLM navigate back to scope
                await page.goto(self.target_url, wait_until="domcontentloaded", timeout=60_000)
                self.tracker.reset_to_main(self.target_url)
                self._scope_drift_count = 0
                await page.wait_for_timeout(1500)

            # 3. Multi-layer context (screenshot + DOM + aria + network + timing)
            console_errors = self._drain_console()
            network_events = self._drain_network()

            ctx, full_dom = await build_page_context(
                page=page,
                step=step,
                mission=self.mission,
                tracker_snapshot=self.tracker.snapshot(),
                action_history=self.log.last_n_actions(10),
                console_error_buffer=console_errors,
                network_event_buffer=network_events,
            )

            # Collect performance metrics per URL change
            if ctx.page_load_ms > 0:
                self.log.perf_metrics.append({
                    "url":     page.url,
                    "step":    step,
                    "load_ms": ctx.page_load_ms,
                    "dom_ms":  0,
                })

            # 4. Filter DOM
            available = self.tracker.available_elements(full_dom)
            ctx.dom_elements = available

            # 5. Save screenshot (compressed JPEG from context_builder)
            screenshot_path = os.path.join(TRACES_DIR, f"step_{step:03d}.jpg")
            with open(screenshot_path, "wb") as f:
                f.write(base64.b64decode(ctx.screenshot_b64))

            # 6. Explorer decision (3 retries)
            decision: NavigationDecision | None = None
            for attempt in range(3):
                try:
                    decision = explorer.decide(ctx)
                    break
                except Exception as e:
                    print(f"  Explorer error (attempt {attempt + 1}/3): {e}")
                    await asyncio.sleep(3)

            if decision is None:
                print("  Explorer failed 3 times. Stopping.")
                break

            print(
                f"\n--- Step {step}/{self.max_steps} "
                f"[{decision.page_type.value}] stay={self.tracker.url_stay_count} ---"
            )
            print(f"  URL    : {page.url[:80]}")
            print(f"  Action : {decision.action.value} -> id={decision.target_id!r}")
            print(f"  Reason : {decision.reasoning[:100]}")
            if ctx.network_errors:
                print(f"  NetErr : {len(ctx.network_errors)} network error(s) this step")
            if ctx.page_load_ms > 3000:
                print(f"  SLOW   : page loaded in {ctx.page_load_ms}ms")
            if decision.suspected_issues:
                print(f"  Hyps   : {len(decision.suspected_issues)} suspected issue(s)")
            if self.mission and self.mission.scope_url_keywords and not self._is_in_scope(page.url):
                print(f"  SCOPE  : outside '{self.mission.test_scope}'")

            # 7. Overrides
            # TYPE is exempt: filling a form is active progress, not being stuck
            if self.tracker.is_stuck and decision.action not in (NavAction.GO_TO_MAIN, NavAction.TYPE):
                print("  [OVERRIDE] Stuck, forcing go_to_main.")
                decision.action = NavAction.GO_TO_MAIN
                decision.target_id = ""

            if decision.action == NavAction.TYPE and not self.mission.allow_typing:
                # Always allow typing on auth pages when credentials are provided.
                # Detect auth pages both by LLM classification and by URL keywords.
                auth_url_keywords = ("login", "signin", "sign-in", "auth", "account", "session", "логин", "вход")
                on_auth = (
                    decision.page_type == PageType.AUTH
                    or any(kw in page.url.lower() for kw in auth_url_keywords)
                )
                has_creds = bool(self.mission.credentials_text)
                if not (on_auth and has_creds):
                    decision.action = NavAction.CLICK

            valid_ids = {el.id for el in available}
            _needs_target = (NavAction.CLICK, NavAction.TYPE, NavAction.HOVER,
                             NavAction.SELECT, NavAction.DOUBLE_CLICK)
            if decision.action in _needs_target:
                if not decision.target_id or decision.target_id not in valid_ids:
                    print(f"  [OVERRIDE] Invalid target_id={decision.target_id!r}, go_to_main.")
                    decision.action = NavAction.GO_TO_MAIN
                    decision.target_id = ""

            # Early exit: no new elements to interact with — site is exhausted
            if not available and decision.action == NavAction.GO_TO_MAIN:
                self._no_elements_streak += 1
                if self._no_elements_streak >= 3:
                    print("  [EARLY EXIT] No new elements for 3 consecutive steps. Session complete.")
                    break
            else:
                self._no_elements_streak = 0

            # Circuit breaker: explorer keeps choosing go_to_main even with elements available
            if decision.action == NavAction.GO_TO_MAIN:
                self._go_to_main_streak += 1
                if self._go_to_main_streak >= 5:
                    print("  [EARLY EXIT] go_to_main loop detected (5 consecutive). Session complete.")
                    break
            else:
                self._go_to_main_streak = 0

            if decision.action == NavAction.TYPE and not decision.value_to_type:
                decision.action = NavAction.CLICK

            # 8. Judge
            verified_issues = await self._run_judge(decision, ctx, screenshot_path)

            # 9. Resolve element text
            target_text = ""
            target_el = None
            if decision.target_id:
                target_el = next((e for e in available if e.id == decision.target_id), None)
                if target_el:
                    target_text = f"[{target_el.tag}] {target_el.text}"
                else:
                    self.tracker.clicked_element_ids.add(decision.target_id)

            # 10. Execute — URL may change
            url_before  = page.url
            await self._execute(page, decision)
            url_after   = page.url
            url_changed = url_before != url_after

            # Typing counts as progress — reset stuck counter so the next CLICK isn't suppressed
            if decision.action == NavAction.TYPE and not url_changed:
                self.tracker.url_stay_count = 0
                # Track if credentials were typed on an auth page (for login failure detection)
                auth_url = any(kw in page.url.lower() for kw in ("login", "signin", "sign-in", "auth"))
                if (decision.page_type == PageType.AUTH or auth_url) and self.mission.credentials_text:
                    self._credentials_typed = True

            # 11. Record click (is_nav only if URL changed)
            if target_el:
                self.tracker.record_click(
                    target_el.id,
                    target_el.text,
                    is_nav=(target_el.tag == "a" and url_changed),
                )

            # 12. Log step
            self.log.add_step(StepLog(
                step=step,
                url=url_before,
                action=decision.action.value,
                target_id=decision.target_id,
                target_text=target_text,
                reasoning=decision.reasoning,
                suspected_issues=decision.suspected_issues,
                verified_issues=verified_issues,
                screenshot_path=screenshot_path,
            ))

            if verified_issues:
                for vi in verified_issues:
                    print(f"  BUG [{vi.severity.upper()}]: {vi.description[:80]}")

            if decision.action == NavAction.DONE:
                print("  Explorer signaled DONE.")
                break

    # ── Judge runner ───────────────────────────────────────────────────────────

    async def _run_judge(
        self,
        decision: NavigationDecision,
        ctx: PageContext,
        screenshot_path: str,
    ) -> list[VerifiedIssue]:
        hypotheses = [h for h in decision.suspected_issues if h.confidence >= 0.4]
        if not hypotheses:
            return []

        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(hypotheses)) as pool:
            futures = [
                loop.run_in_executor(pool, judge.verify, h, ctx, screenshot_path)
                for h in hypotheses
            ]
            results = await asyncio.gather(*futures, return_exceptions=True)

        verified = []
        for r in results:
            if isinstance(r, VerifiedIssue):
                if not any(v.description == r.description for v in self.log.verified_issues):
                    verified.append(r)
            elif isinstance(r, Exception):
                print(f"  Judge error: {r}")
        return verified

    # ── Action executor ────────────────────────────────────────────────────────

    async def _execute(self, page: Page, decision: NavigationDecision) -> None:
        try:
            if decision.action == NavAction.CLICK and decision.target_id:
                target = page.locator(f"[qa-id='{decision.target_id}']").first
                await target.click(timeout=5000, force=True)

            elif decision.action == NavAction.TYPE and decision.target_id:
                target = page.locator(f"[qa-id='{decision.target_id}']").first
                await target.click(timeout=3000, force=True)
                await target.fill(decision.value_to_type)
                # No auto-Enter — agent must explicitly CLICK the submit button
                # or use press_key action. Auto-Enter breaks multi-field forms
                # (typing email and pressing Enter submits before password is entered)

            elif decision.action == NavAction.GO_TO_MAIN:
                await page.goto(self.target_url, wait_until="domcontentloaded", timeout=60_000)
                self.tracker.reset_to_main(self.target_url)

            elif decision.action == NavAction.PRESS_KEY and decision.target_id:
                await page.keyboard.press(decision.target_id)

            elif decision.action == NavAction.SCROLL_DOWN:
                await page.evaluate("window.scrollBy(0, window.innerHeight)")

            elif decision.action == NavAction.HOVER and decision.target_id:
                target = page.locator(f"[qa-id='{decision.target_id}']").first
                await target.hover(timeout=5000)

            elif decision.action == NavAction.SELECT and decision.target_id:
                target = page.locator(f"[qa-id='{decision.target_id}']").first
                if decision.value_to_type:
                    try:
                        await target.select_option(label=decision.value_to_type, timeout=5000)
                    except Exception:
                        await target.select_option(value=decision.value_to_type, timeout=3000)
                else:
                    await target.select_option(index=1, timeout=3000)

            elif decision.action == NavAction.DOUBLE_CLICK and decision.target_id:
                target = page.locator(f"[qa-id='{decision.target_id}']").first
                await target.dblclick(timeout=5000, force=True)

            elif decision.action == NavAction.DONE:
                pass

        except Exception as e:
            print(f"  Action error: {e}")

    # ── Report writer ──────────────────────────────────────────────────────────

    def _write_report(self) -> str:
        mode = self.mission.session_mode

        # API summary (only if API mode and results exist)
        api_summary = ""
        if mode == SessionMode.API and self.log.api_results:
            api_summary = api_tester.summarize(self.log.api_results, self.target_url)

        # API mode: always show the section (even if empty — explain why)
        # Other modes: show captured endpoints if any were observed
        if mode == SessionMode.API:
            api_results_for_report = self.log.api_results if self.log.api_results else []
        elif self.log.api_endpoints:
            api_results_for_report = [
                {"url": info["url"], "method": info["method"],
                 "status": info["status"], "duration_ms": 0, "captured_only": True}
                for info in self.log.api_endpoints.values()
            ]
        else:
            api_results_for_report = None

        content = reporter.generate(
            mission=self.mission,
            target_url=self.target_url,
            user_task=self.user_task,
            steps=self.log.steps,
            verified_issues=self.log.verified_issues,
            journey_screenshots=self.log.journey_screenshots,
            network_events=self.log.network_events if mode == SessionMode.NETWORK else None,
            api_results=api_results_for_report,
            api_summary=api_summary,
            perf_metrics=self.log.perf_metrics if mode == SessionMode.LOAD_PERFORMANCE else None,
            load_test_results=(
                self.log.load_test_results if mode == SessionMode.LOAD_PERFORMANCE else None
            ),
        )
        os.makedirs(REPORTS_DIR, exist_ok=True)
        ts       = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(REPORTS_DIR, f"QA_Report_{ts}.md")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\nReport saved: {filename}")

        # Also generate Word (.docx) with embedded screenshots per bug
        try:
            from docx_writer import write_docx
            docx_path = write_docx(
                md_path=filename,
                mission=self.mission,
                target_url=self.target_url,
                user_task=self.user_task,
                verified_issues=self.log.verified_issues,
                steps=self.log.steps,
            )
            print(f"Word report:  {docx_path}")
        except Exception as e:
            print(f"[docx] Warning: could not generate Word report: {e}")

        return filename
