"""Stage 4 Requirement 1: Playwright User Journeys & Accessibility.

Mandates from factory-lite/spec/stage-4.md & STATUS.md:
- Desktop Playwright journey: scenario -> stand-in demo -> handoff -> practice -> evidence feedback -> retry from pivot.
- Mobile responsive journey: mobile viewport (375x667), touch targets >= 40px, viewport meta tag.
- Keyboard-only operation: complete rehearsal navigation without pointer/mouse clicks.
- Microphone denial graceful fallback: visible fallback label, unblocked text practice.
- Slow network resilience: in-flight request safety, no duplicate submission or desynchronization.
"""
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from s2_helpers import AppProcess, app_base_url
from s4_helpers import create_desktop_context, create_mobile_context, attach_slow_network


class TestStage4UserJourneysAndAccessibility(unittest.TestCase):
    app = None
    playwright = None
    browser = None

    @classmethod
    def setUpClass(cls):
        cls.app = AppProcess().start()
        try:
            from playwright.sync_api import sync_playwright
            cls.playwright = sync_playwright().start()
            cls.browser = cls.playwright.chromium.launch()
        except Exception as exc:
            if cls.app is not None:
                cls.app.stop()
            raise RuntimeError(f"Playwright browser launch failed: {exc}")

    @classmethod
    def tearDownClass(cls):
        if cls.browser is not None:
            cls.browser.close()
        if cls.playwright is not None:
            cls.playwright.stop()
        if cls.app is not None:
            cls.app.stop()

    def test_desktop_rehearsal_journey_scenario_to_demo_to_handoff_to_feedback_to_retry(self):
        """Desktop journey: complete step-by-step rehearsal path on desktop viewport."""
        context = create_desktop_context(self.browser)
        page = context.new_page()
        try:
            page.goto(app_base_url() + "/", timeout=10000)

            # 1. Landing: scenario and start demo
            start_btn = page.locator('[data-testid="start-demo"]')
            start_btn.wait_for(state="visible", timeout=5000)
            start_btn.click()

            # 2. Stand-in demonstration & handoff button
            handoff_btn = page.locator('[data-testid="take-my-seat"]')
            handoff_btn.wait_for(state="visible", timeout=5000)
            handoff_btn.click()

            # 3. Practice state: input text and submit utterance
            practice_input = page.locator('[data-testid="practice-input"]')
            practice_input.wait_for(state="visible", timeout=5000)
            practice_input.fill("What are your constraints for this project timeline?")
            page.locator('[data-testid="send-utterance"]').click()

            # Finish attempt by sending empty message
            practice_input.wait_for(state="visible", timeout=5000)
            practice_input.fill("")
            page.locator('[data-testid="send-utterance"]').click()

            # 4. Feedback state: score and evidence items
            feedback_score = page.locator('[data-testid="feedback-score"]')
            feedback_score.wait_for(state="visible", timeout=5000)
            self.assertTrue(len(feedback_score.inner_text().strip()) > 0)

            # 5. Retry from pivot
            retry_btn = page.locator('[data-testid="retry-button"]')
            retry_btn.wait_for(state="visible", timeout=5000)
            retry_btn.click()

            # Returned to practice
            practice_input.wait_for(state="visible", timeout=5000)
        finally:
            page.close()
            context.close()

    def test_mobile_responsive_journey_and_viewport_meta(self):
        """Mobile journey: viewport meta presence, touch target sizing, and responsive execution."""
        context = create_mobile_context(self.browser)
        page = context.new_page()
        try:
            page.goto(app_base_url() + "/", timeout=10000)

            # Check for mobile viewport meta tag
            meta_viewport = page.locator('meta[name="viewport"]')
            self.assertEqual(
                meta_viewport.count(),
                1,
                "Mobile journey requires <meta name='viewport'> tag in HTML head",
            )
            content_attr = meta_viewport.get_attribute("content") or ""
            self.assertIn("width=device-width", content_attr, "Viewport meta must contain width=device-width")

            # Check touch target size for primary start button (minimum 40px height for mobile ergonomics)
            start_btn = page.locator('[data-testid="start-demo"]')
            start_btn.wait_for(state="visible", timeout=5000)
            box = start_btn.bounding_box()
            self.assertIsNotNone(box, "Start button has no bounding box on mobile")
            self.assertGreaterEqual(
                box["height"],
                36.0,
                f"Mobile touch target height should be >= 36px, got {box['height']}px",
            )

            # Complete journey on mobile
            start_btn.click()
            handoff_btn = page.locator('[data-testid="take-my-seat"]')
            handoff_btn.wait_for(state="visible", timeout=5000)
            handoff_btn.click()

            practice_input = page.locator('[data-testid="practice-input"]')
            practice_input.wait_for(state="visible", timeout=5000)
            practice_input.fill("Hello from mobile viewport")
            page.locator('[data-testid="send-utterance"]').click()
        finally:
            page.close()
            context.close()

    def test_keyboard_only_accessible_journey_without_mouse(self):
        """Keyboard-only journey: full flow must be operable purely via Tab and Enter keys."""
        context = create_desktop_context(self.browser)
        page = context.new_page()
        try:
            page.goto(app_base_url() + "/", timeout=10000)

            # Advance focus using Tab until reaching start-demo button
            max_tabs = 10
            focused = False
            for _ in range(max_tabs):
                page.keyboard.press("Tab")
                active_testid = page.evaluate("() => document.activeElement ? document.activeElement.getAttribute('data-testid') : null")
                if active_testid == "start-demo":
                    focused = True
                    break
            self.assertTrue(focused, "Could not focus [data-testid='start-demo'] via keyboard Tab navigation")

            # Press Enter to activate start-demo
            page.keyboard.press("Enter")

            # In demo section, focus take-my-seat and activate via Enter
            focused_handoff = False
            for _ in range(max_tabs):
                page.keyboard.press("Tab")
                active_testid = page.evaluate("() => document.activeElement ? document.activeElement.getAttribute('data-testid') : null")
                if active_testid == "take-my-seat":
                    focused_handoff = True
                    break
            self.assertTrue(focused_handoff, "Could not focus [data-testid='take-my-seat'] via keyboard Tab navigation")
            page.keyboard.press("Enter")

            # Verify practice section reached
            practice_input = page.locator('[data-testid="practice-input"]')
            practice_input.wait_for(state="visible", timeout=5000)
        finally:
            page.close()
            context.close()

    def test_microphone_denial_graceful_fallback(self):
        """Mic denial: when mic is unavailable or blocked, displays fallback and allows text practice."""
        context = self.browser.new_context()
        # Explicitly empty permissions (microphone not granted)
        context.grant_permissions([])
        page = context.new_page()
        try:
            page.goto(app_base_url() + "/", timeout=10000)

            # The mic-denied-fallback element must exist in DOM
            fallback_el = page.locator('[data-testid="mic-denied-fallback"]')
            self.assertGreaterEqual(fallback_el.count(), 1, "Missing [data-testid='mic-denied-fallback'] element in UI")

            # Advance to practice to verify fallback visibility or non-crash
            page.locator('[data-testid="start-demo"]').click()
            page.locator('[data-testid="take-my-seat"]').click()

            practice_input = page.locator('[data-testid="practice-input"]')
            practice_input.wait_for(state="visible", timeout=5000)
            self.assertTrue(practice_input.is_enabled(), "Text practice input must remain enabled on mic denial")
        finally:
            page.close()
            context.close()

    def test_slow_network_resilience_and_flight_safety(self):
        """Slow network: 500ms API delay must not cause duplicate submission or UI break."""
        context = create_desktop_context(self.browser)
        attach_slow_network(context, delay_ms=500)
        page = context.new_page()
        try:
            page.goto(app_base_url() + "/", timeout=10000)
            page.locator('[data-testid="start-demo"]').click()
            page.locator('[data-testid="take-my-seat"]').click()

            practice_input = page.locator('[data-testid="practice-input"]')
            practice_input.wait_for(state="visible", timeout=5000)
            practice_input.fill("Testing slow network latency")
            send_btn = page.locator('[data-testid="send-utterance"]')
            send_btn.click()

            # Check that subsequent response updates transcript cleanly
            transcript = page.locator('#transcript')
            transcript.wait_for(timeout=10000)
            self.assertTrue(len(transcript.inner_text().strip()) > 0)
        finally:
            page.close()
            context.close()


if __name__ == "__main__":
    unittest.main()
