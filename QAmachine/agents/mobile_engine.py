"""
Mobile Engine — device presets and mobile-specific explorer guidance.

Provides:
  - DEVICE_PRESETS: dict of named device configs
  - get_device_config(): lookup by name with fuzzy fallback
  - mobile_mode_rules(): mode-specific explorer prompt block for MOBILE session
"""
from __future__ import annotations
from schemas import MobileConfig

# ── Device presets ─────────────────────────────────────────────────────────────

DEVICE_PRESETS: dict[str, MobileConfig] = {
    "iPhone 12": MobileConfig(
        device_name="iPhone 12",
        viewport_width=390,
        viewport_height=844,
        user_agent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/14.0 Mobile/15E148 Safari/604.1"
        ),
        is_mobile=True,
        has_touch=True,
        device_scale_factor=3.0,
    ),
    "iPhone SE": MobileConfig(
        device_name="iPhone SE",
        viewport_width=375,
        viewport_height=667,
        user_agent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/15.0 Mobile/15E148 Safari/604.1"
        ),
        is_mobile=True,
        has_touch=True,
        device_scale_factor=2.0,
    ),
    "iPhone 14 Pro": MobileConfig(
        device_name="iPhone 14 Pro",
        viewport_width=393,
        viewport_height=852,
        user_agent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/16.0 Mobile/15E148 Safari/604.1"
        ),
        is_mobile=True,
        has_touch=True,
        device_scale_factor=3.0,
    ),
    "Pixel 5": MobileConfig(
        device_name="Pixel 5",
        viewport_width=393,
        viewport_height=851,
        user_agent=(
            "Mozilla/5.0 (Linux; Android 11; Pixel 5) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/90.0.4430.91 Mobile Safari/537.36"
        ),
        is_mobile=True,
        has_touch=True,
        device_scale_factor=2.75,
    ),
    "Galaxy S21": MobileConfig(
        device_name="Galaxy S21",
        viewport_width=360,
        viewport_height=800,
        user_agent=(
            "Mozilla/5.0 (Linux; Android 11; Samsung Galaxy S21) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/90.0.4430.210 Mobile Safari/537.36 SamsungBrowser/14.0"
        ),
        is_mobile=True,
        has_touch=True,
        device_scale_factor=3.0,
    ),
    "iPad": MobileConfig(
        device_name="iPad",
        viewport_width=810,
        viewport_height=1080,
        user_agent=(
            "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/14.0 Mobile/15E148 Safari/604.1"
        ),
        is_mobile=True,
        has_touch=True,
        device_scale_factor=2.0,
    ),
}

DEFAULT_DEVICE = "iPhone 12"


def get_device_config(device_name: str) -> MobileConfig:
    """Return MobileConfig for the given device name. Case-insensitive, falls back to iPhone 12."""
    for key in DEVICE_PRESETS:
        if key.lower() == device_name.lower():
            return DEVICE_PRESETS[key]
    # Partial match
    for key in DEVICE_PRESETS:
        if device_name.lower() in key.lower() or key.lower() in device_name.lower():
            return DEVICE_PRESETS[key]
    return DEVICE_PRESETS[DEFAULT_DEVICE]


# ── Mobile-specific explorer strategy block ────────────────────────────────────

def mobile_mode_rules(device_name: str, check_type: str = "functional") -> str:
    """Returns the MOBILE mode block injected into the explorer system prompt."""
    check_focus = {
        "ui_ux": (
            "FOCUS: VISUAL mobile issues only.\n"
            "Look for layout breaks, overflow, overlapping, unreadable text, broken images.\n"
            "Do NOT test functional behavior."
        ),
        "regression": (
            "FOCUS: REGRESSION on mobile — did the recent changes break mobile layout or behavior?\n"
            "Test changed areas first, then neighboring zones, then smoke related flows."
        ),
        "functional": (
            "FOCUS: FUNCTIONAL on mobile — do features work correctly at this viewport?\n"
            "Test forms, navigation, buttons, search, modals, CTAs."
        ),
    }.get(check_type, "FOCUS: Functional mobile testing.")

    return f"""
== MODE: MOBILE TESTING [{device_name}] =============================================
You are testing a REAL site on a MOBILE device. Viewport is narrow ({device_name}).
{check_focus}

MANDATORY MOBILE CHECKS — always inspect these (report as suspected_issues if broken):

1. HORIZONTAL SCROLL
   Is the page wider than the viewport? Does any element cause horizontal overflow?
   (Evidence: scroll indicator, element sticking out right edge)

2. TOUCH TARGETS
   Are buttons/links/CTAs smaller than ~44x44px? Hard to tap?
   Look for: very small buttons, links packed too close together.

3. BURGER / HAMBURGER MENU
   Is there a burger icon in the header? Click it. Does the menu open correctly?
   Does it overlay content properly? Can it be closed?

4. TEXT OVERFLOW & TRUNCATION
   Is any text cut off, overflowing its container, or unreadably small (<12px)?

5. OVERLAPPING ELEMENTS
   Are any elements sitting on top of each other unintentionally?
   (Sticky header covering content, floating button hiding CTAs)

6. STICKY HEADER / FOOTER
   If there's a sticky top bar or bottom navigation — does it cover page content?
   Is it the right size? Does it scroll correctly?

7. MOBILE FORMS
   Do input fields take the full available width?
   Do they trigger correct keyboard type? Are labels visible?

8. MODALS & OVERLAYS
   If you open a modal/popup — does it fit the screen?
   Can it be closed? Does it scroll internally if content is long?

9. IMAGES
   Are images scaling correctly? Any image overflowing the viewport?
   Any broken images?

10. CTA VISIBILITY
    Are primary action buttons visible without having to scroll excessively?

NAVIGATION STRATEGY:
- Always try the burger/hamburger menu first if visible
- Scroll down to reveal full page content (use scroll_down)
- Interact with forms and modals to check mobile behavior
- Check each main navigation section
- Use go_to_main only if truly stuck (stay count >= 8)

OUTPUT: suspected_issues = mobile-specific UX/functional problems ONLY.
Do NOT flag purely desktop-design decisions as mobile bugs.
================================================================================="""
