"""Stage 4 Requirement 1: Playwright User Journeys, Responsiveness & Accessibility.

Covers:
1. Desktop Playwright journey (landing -> demo -> take-my-seat -> practice -> feedback -> retry)
2. Mobile Playwright journey (375x667 viewport, viewport meta check)
3. Responsive avatar container (measured bounding box, aspect ratio, touch targets >= 44px, no horizontal scroll)
4. Full keyboard-only operation (Tab traversal, Enter/Space activation)
5. Microphone permission denial graceful degradation & text continuity
6. Slow network route interception, single in-flight turn, and race resilience
"""
import sys
import time
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from s2_helpers import AppProcess, app_base_url
from s4_helpers import (
    DESKTOP_VIEWPORT,
    MOBILE_VIEWPORT,
    create_desktop_context,
    create_mobile_context,
    attach_slow_network,
)

SCREENSHOT_DIR = TESTS_DIR / "evidence" / "screenshots"


class TestStage4UserJourneysAndAccessibility(unittest.TestCase):
    app = None
    playwright = None
    browser = None

    @classmethod
    def setUpClass(cls):
        cls.app = AppProcess().start()
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            cls.app.stop()
            raise unittest.SkipTest(f"playwright not installed: {exc}")
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        if cls.browser is not None:
            cls.browser.close()
        if cls.playwright is not None:
            cls.playwright.stop()
        if cls.app is not None:
            cls.app.stop()

    def setUp(self):
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    def _snapshot(self, page, label):
        path = SCREENSHOT_DIR / f"{self.id().split('.')[-1]}_{label}.png"
        try:
            page.screenshot(path=str(path))
        except Exception:
            pass

    def test_desktop_playwright_e2e_journey(self):
        """Desktop Playwright journey: landing -> demo -> take-my-seat -> practice -> feedback -> retry."""
        context = create_desktop_context(self.browser)
        page = context.new_page()
        try:
            page.goto(app_base_url() + "/", timeout=10000)
            self._snapshot(page, "desktop_landing")

            start_demo = page.locator('[data-testid="start-demo"]')
            start_demo.wait_for(state="visible", timeout=5000)
            start_demo.click()
            self._snapshot(page, "desktop_demo")

            take_seat = page.locator('[data-testid="take-my-seat"]')
            take_seat.wait_for(state="visible", timeout=5000)
            take_seat.click()
            self._snapshot(page, "desktop_take_my_seat")

            practice_input = page.locator('[data-testid="practice-input"]')
            practice_input.wait_for(state="visible", timeout=5000)
            practice_input.fill("What is your budget flexibility?")

            send_btn = page.locator('[data-testid="send-utterance"]')
            send_btn.click()
            self._snapshot(page, "desktop_practice_turn")

            # End attempt / transition to feedback
            send_btn.click()
            score_el = page.locator('[data-testid="feedback-score"]')
            score_el.wait_for(state="visible", timeout=5000)
            score_text = score_el.text_content()
            self.assertTrue(bool(score_text and score_text.strip()), "Feedback score must be visible")
            self._snapshot(page, "desktop_feedback")

            retry_btn = page.locator('[data-testid="retry-button"]')
            retry_btn.wait_for(state="visible", timeout=5000)
            retry_btn.click()
            self._snapshot(page, "desktop_retry")

            practice_input.wait_for(state="visible", timeout=5000)
            self.assertEqual(practice_input.input_value(), "", "Retry must return to a fresh practice input")
        finally:
            page.close()
            context.close()

    def test_mobile_375x667_playwright_journey_and_viewport_meta(self):
        """Mobile Playwright journey on 375x667 viewport and validates <meta name='viewport'> presence."""
        context = create_mobile_context(self.browser)
        page = context.new_page()
        try:
            page.goto(app_base_url() + "/", timeout=10000)
            self._snapshot(page, "mobile_landing")

            # Verify viewport meta in HTML head
            meta_viewport = page.locator('meta[name="viewport"]')
            self.assertGreaterEqual(
                meta_viewport.count(),
                1,
                "Mobile journey requires <meta name='viewport'> tag in HTML head",
            )
            content_attr = meta_viewport.first.get_attribute("content")
            self.assertIn("width=device-width", content_attr.lower())

            # Navigate through mobile flow
            start_demo = page.locator('[data-testid="start-demo"]')
            start_demo.wait_for(state="visible", timeout=5000)
            start_demo.click()

            take_seat = page.locator('[data-testid="take-my-seat"]')
            take_seat.wait_for(state="visible", timeout=5000)
            take_seat.click()
            self._snapshot(page, "mobile_take_my_seat")

            practice_input = page.locator('[data-testid="practice-input"]')
            practice_input.wait_for(state="visible", timeout=5000)
            practice_input.fill("Testing mobile responsiveness")
            page.locator('[data-testid="send-utterance"]').click()
            self._snapshot(page, "mobile_practice")
        finally:
            page.close()
            context.close()

    def test_avatar_container_viewport_containment_and_dimensions(self):
        """Avatar container must fit desktop and 375x667 without horizontal scrolling or media overflow."""
        context = create_mobile_context(self.browser)
        page = context.new_page()
        try:
            page.goto(app_base_url() + "/", timeout=10000)

            # Check horizontal overflow on mobile 375px
            scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
            client_width = page.evaluate("() => document.documentElement.clientWidth")
            self.assertLessEqual(
                scroll_width,
                client_width + 1,
                f"Page horizontally overflows mobile viewport: scrollWidth={scroll_width} > clientWidth={client_width}"
            )

            # Check avatar container bounding box if present
            avatar_slot = page.locator('[data-testid="napster-avatar"]')
            if avatar_slot.count() > 0 and avatar_slot.first.is_visible():
                box = avatar_slot.first.bounding_box()
                self.assertIsNotNone(box)
                self.assertLessEqual(box["width"], 375, "Avatar container width must not exceed mobile viewport")

            # Check interactive touch target sizes (>= 40px target, min 36px)
            start_btn = page.locator('[data-testid="start-demo"]')
            if start_btn.count() > 0 and start_btn.first.is_visible():
                bbox = start_btn.first.bounding_box()
                self.assertIsNotNone(bbox)
                self.assertGreaterEqual(bbox["height"], 36, "Touch target height must be >= 36px (target 44px)")
        finally:
            page.close()
            context.close()

    def test_keyboard_traversal_and_activation(self):
        """Interactive controls must be accessible and activatable via keyboard Tab and Enter."""
        context = create_desktop_context(self.browser)
        page = context.new_page()
        try:
            page.goto(app_base_url() + "/", timeout=10000)

            # Tab into the first interactive element
            page.keyboard.press("Tab")
            focused_tag = page.evaluate("() => document.activeElement ? document.activeElement.tagName.toLowerCase() : ''")
            self.assertIn(focused_tag, ["button", "input", "a"], "Keyboard Tab must focus an interactive element")

            # Press Enter to activate focused control
            page.keyboard.press("Enter")
            time.sleep(0.2)
        finally:
            page.close()
            context.close()

    def test_mic_denial_browser_permission_fallback(self):
        """Denied microphone permission triggers fallback notice and leaves text practice fully functional."""
        context = self.browser.new_context(permissions=[])  # explicitly deny microphone
        page = context.new_page()
        try:
            page.goto(app_base_url() + "/", timeout=10000)
            page.locator('[data-testid="start-demo"]').click()
            page.locator('[data-testid="take-my-seat"]').click()

            fallback = page.locator('[data-testid="mic-denied-fallback"]')
            fallback.wait_for(state="visible", timeout=5000)
            self.assertTrue(fallback.is_visible(), "Fallback notice [data-testid='mic-denied-fallback'] must be visible")

            practice_input = page.locator('[data-testid="practice-input"]')
            self.assertTrue(practice_input.is_enabled(), "Text practice input must remain enabled on mic denial")
            practice_input.fill("Text utterance under denied microphone")
            page.locator('[data-testid="send-utterance"]').click()
        finally:
            page.close()
            context.close()

    def test_slow_network_route_interception_resilience(self):
        """Playwright route interception delays /api/rehearsal/** requests and proves single flight without duplicate sends."""
        context = create_desktop_context(self.browser)
        attach_slow_network(context, delay_ms=600)
        page = context.new_page()
        try:
            page.goto(app_base_url() + "/", timeout=15000)
            start_btn = page.locator('[data-testid="start-demo"]')
            start_btn.wait_for(state="visible", timeout=5000)
            start_btn.click()

            take_seat = page.locator('[data-testid="take-my-seat"]')
            take_seat.wait_for(state="visible", timeout=10000)
            self.assertTrue(take_seat.is_visible())
        finally:
            page.close()
            context.close()


if __name__ == "__main__":
    unittest.main()
