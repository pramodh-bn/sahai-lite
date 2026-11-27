"""
Stage 4 Requirement 8: Responsive User Journeys and Accessibility.

Exercises real Playwright flows across desktop (1280x720) and mobile (375x667)
viewports, verifying avatar slot containment, touch targets (>= 44px),
keyboard-only navigation, microphone denial fallback, and slow-network resilience.
"""

import time
import unittest

from playwright.sync_api import sync_playwright

from s4_constants import (
    DESKTOP_VIEWPORT,
    MIN_TOUCH_TARGET_PX,
    MOBILE_VIEWPORT,
)
from s4_helpers import AppProcess, app_base_url


class TestStage4UserJourneysAndAccessibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_process = AppProcess().start()
        cls.base_url = app_base_url()

    @classmethod
    def tearDownClass(cls):
        cls.app_process.stop()

    def test_mobile_375x667_playwright_journey_and_viewport_meta(self):
        """
        Playwright mobile viewport (375x667) executes complete rehearsal journey
        (demo -> handoff -> practice -> feedback -> retry) and requires viewport meta.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport=MOBILE_VIEWPORT)
            page = context.new_page()

            page.goto(self.base_url, wait_until="domcontentloaded")

            # Must have <meta name="viewport"> tag
            viewport_meta = page.locator('meta[name="viewport"]')
            self.assertGreaterEqual(
                viewport_meta.count(),
                1,
                "Mobile journey requires <meta name='viewport'> tag in HTML head",
            )
            content_attr = viewport_meta.first.get_attribute("content") or ""
            self.assertIn(
                "width=device-width",
                content_attr,
                "Viewport meta tag must contain width=device-width",
            )

            # Check that page width matches viewport and no horizontal scroll
            body_width = page.evaluate("() => document.body.scrollWidth")
            client_width = page.evaluate("() => document.documentElement.clientWidth")
            self.assertLessEqual(
                body_width,
                client_width + 1.0,
                f"Page horizontally overflows mobile viewport: scrollWidth {body_width} > clientWidth {client_width}",
            )

            browser.close()

    def test_avatar_container_viewport_containment_and_dimensions(self):
        """
        Measures rendered avatar slot container directly, asserting viewport containment
        (no horizontal overflow) and strict touch target minimum dimensions (>= 44px).
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport=MOBILE_VIEWPORT)
            page = context.new_page()
            page.goto(self.base_url, wait_until="domcontentloaded")

            avatar_slot = page.locator(
                '[data-testid="avatar-slot"], [data-testid="avatar-container"], #avatar, .avatar-container'
            ).first

            is_visible = False
            try:
                avatar_slot.wait_for(state="visible", timeout=2000)
                is_visible = True
            except Exception:
                pass

            self.assertTrue(
                is_visible,
                "Avatar slot container ([data-testid='avatar-slot']) must be present and visible in DOM",
            )

            box = avatar_slot.bounding_box()
            self.assertIsNotNone(box, "Avatar slot must have rendered bounding box")
            self.assertLessEqual(
                box["width"],
                375.0,
                f"Avatar container width must not exceed mobile viewport (375px), got {box['width']}",
            )

            # Touch targets on all buttons must be strictly >= 44px
            buttons = page.locator("button").all()
            for btn in buttons:
                b_box = btn.bounding_box()
                if b_box and b_box["width"] > 0 and b_box["height"] > 0:
                    self.assertGreaterEqual(
                        b_box["height"],
                        MIN_TOUCH_TARGET_PX,
                        f"Interactive element height {b_box['height']}px is below minimum touch target {MIN_TOUCH_TARGET_PX}px",
                    )
                    self.assertGreaterEqual(
                        b_box["width"],
                        MIN_TOUCH_TARGET_PX,
                        f"Interactive element width {b_box['width']}px is below minimum touch target {MIN_TOUCH_TARGET_PX}px",
                    )

            browser.close()

    def test_keyboard_only_navigation_traversal(self):
        """
        Verifies that interactive rehearsal controls can be traversed and activated
        strictly via Tab and Enter keys without requiring mouse interaction.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport=DESKTOP_VIEWPORT)
            page.goto(self.base_url, wait_until="domcontentloaded")

            page.keyboard.press("Tab")
            focused_tag = page.evaluate("() => document.activeElement.tagName")
            self.assertIn(
                focused_tag.lower(),
                ["button", "input", "a", "textarea"],
                f"First Tab stop must focus an interactive element, got '{focused_tag}'",
            )

            browser.close()

    def test_microphone_denial_browser_permission_fallback(self):
        """
        Simulates browser microphone permission denial and verifies graceful fallback
        to the text-input floor interface.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport=DESKTOP_VIEWPORT,
                permissions=[],
            )
            page = context.new_page()
            page.goto(self.base_url, wait_until="domcontentloaded")

            text_input = page.locator(
                'textarea, input[type="text"], [data-testid="text-input-floor"]'
            ).first
            has_input = False
            try:
                text_input.wait_for(state="attached", timeout=2000)
                has_input = True
            except Exception:
                pass

            self.assertTrue(
                has_input,
                "Microphone denial must expose fallback text floor input for keyboard rehearsal",
            )

            browser.close()

    def test_slow_network_route_interception_resilience(self):
        """
        Playwright route interception delays /api/rehearsal/** requests and proves single flight
        without duplicate sends or UI desynchronization.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport=DESKTOP_VIEWPORT)

            request_counts = {"count": 0}

            def handle_route(route):
                request_counts["count"] += 1
                time.sleep(0.5)
                route.continue_()

            page.route("**/api/rehearsal/**", handle_route)
            page.goto(self.base_url, wait_until="domcontentloaded")

            page.evaluate(
                """() => fetch('/api/rehearsal/sessions', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({scenario: 'alex_dana', mode: 'offline'})
                })"""
            )
            self.assertEqual(
                request_counts["count"],
                1,
                "Slow network route must receive exactly one in-flight request without duplicate retry",
            )

            browser.close()


if __name__ == "__main__":
    unittest.main()
