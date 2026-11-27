"""
Stage 4 Requirement 8: Responsive User Journeys and Accessibility.

Executes complete real Playwright journeys across desktop (1280x720) and mobile (375x667)
viewports through demo -> handoff -> practice -> feedback -> retry.
Measures exact [data-testid="avatar-slot"], child media elements, and interactive controls (>= 44px)
without selector fallbacks, swallowed timeouts, or conditional guards.
Verifies keyboard traversal, microphone permission denial fallback, and slow-network single flight.
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

    def test_desktop_1280x720_complete_playwright_journey(self):
        """
        Desktop 1280x720 viewport executes complete journey:
        demo -> handoff -> practice -> feedback -> retry.
        Measures exact [data-testid="avatar-slot"], child media elements, and touch targets >= 44px.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport=DESKTOP_VIEWPORT)
            page.goto(self.base_url, wait_until="domcontentloaded")

            # 1. Landing and Avatar Slot Verification
            avatar_slot = page.locator('[data-testid="avatar-slot"]')
            self.assertTrue(avatar_slot.is_visible(), "Avatar slot [data-testid='avatar-slot'] must be visible in UI")
            a_box = avatar_slot.bounding_box()
            self.assertIsNotNone(a_box, "Avatar slot must have a rendered bounding box")
            self.assertGreater(a_box["width"], 0, "Avatar slot width must be positive")
            self.assertGreater(a_box["height"], 0, "Avatar slot height must be positive")

            # Measure media element within avatar slot
            media_el = page.locator('[data-testid="avatar-video"]')
            self.assertTrue(media_el.is_visible(), "Avatar media element must be visible in UI")
            m_box = media_el.bounding_box()
            self.assertIsNotNone(m_box, "Avatar media element must have a rendered bounding box")
            self.assertGreater(m_box["width"], 0)
            self.assertGreater(m_box["height"], 0)

            # 2. Interactive control: connect button must satisfy MIN_TOUCH_TARGET_PX
            connect_btn = page.locator('[data-testid="connect-button"]')
            self.assertTrue(connect_btn.is_visible(), "Connect button must be visible in UI")
            b_box = connect_btn.bounding_box()
            self.assertIsNotNone(b_box, "Connect button must have a rendered bounding box")
            self.assertGreaterEqual(b_box["height"], MIN_TOUCH_TARGET_PX)
            self.assertGreaterEqual(b_box["width"], MIN_TOUCH_TARGET_PX)

            # 3. Step 1: Demo phase
            demo_section = page.locator('[data-testid="demo-phase"]')
            self.assertTrue(demo_section.is_visible(), "Demo phase section must be visible")
            start_btn = page.locator('[data-testid="start-handoff-button"]')
            self.assertTrue(start_btn.is_visible(), "Start handoff button must be visible")
            start_btn.click()

            # 4. Step 2: Handoff phase
            handoff_section = page.locator('[data-testid="handoff-phase"]')
            self.assertTrue(handoff_section.is_visible(), "Handoff phase section must be visible")
            enter_btn = page.locator('[data-testid="enter-practice-button"]')
            self.assertTrue(enter_btn.is_visible(), "Enter practice button must be visible")
            enter_btn.click()

            # 5. Step 3: Practice phase
            practice_section = page.locator('[data-testid="practice-phase"]')
            self.assertTrue(practice_section.is_visible(), "Practice phase section must be visible")
            text_input = page.locator('[data-testid="user-utterance-input"]')
            self.assertTrue(text_input.is_visible(), "User utterance input must be visible")
            text_input.fill("Hello Alex, let's begin.")
            send_btn = page.locator('[data-testid="send-turn-button"]')
            self.assertTrue(send_btn.is_visible(), "Send turn button must be visible")
            send_btn.click()

            # Advance to feedback
            feedback_nav_btn = page.locator('[data-testid="view-feedback-button"]')
            self.assertTrue(feedback_nav_btn.is_visible(), "View feedback button must be visible")
            feedback_nav_btn.click()

            # 6. Step 4: Feedback phase
            feedback_section = page.locator('[data-testid="feedback-phase"]')
            self.assertTrue(feedback_section.is_visible(), "Feedback phase section must be visible")

            # 7. Step 5: Retry phase
            retry_btn = page.locator('[data-testid="retry-practice-button"]')
            self.assertTrue(retry_btn.is_visible(), "Retry practice button must be visible")
            retry_btn.click()

            # Verify return to practice phase
            self.assertTrue(practice_section.is_visible(), "Retry must navigate back to practice phase")

            browser.close()

    def test_mobile_375x667_complete_playwright_journey(self):
        """
        Mobile 375x667 viewport executes complete journey:
        demo -> handoff -> practice -> feedback -> retry.
        Measures exact [data-testid="avatar-slot"], child media elements, and touch targets >= 44px.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport=MOBILE_VIEWPORT)
            page.goto(self.base_url, wait_until="domcontentloaded")

            # 1. Viewport meta tag presence
            viewport_meta = page.locator('meta[name="viewport"]')
            self.assertEqual(viewport_meta.count(), 1, "Mobile page must specify a viewport meta tag")

            # 2. Avatar slot measurement
            avatar_slot = page.locator('[data-testid="avatar-slot"]')
            self.assertTrue(avatar_slot.is_visible(), "Mobile avatar slot must be visible")
            a_box = avatar_slot.bounding_box()
            self.assertIsNotNone(a_box)
            self.assertGreater(a_box["width"], 0)
            self.assertGreater(a_box["height"], 0)

            media_el = page.locator('[data-testid="avatar-video"]')
            self.assertTrue(media_el.is_visible(), "Mobile media element must be visible")
            m_box = media_el.bounding_box()
            self.assertIsNotNone(m_box)
            self.assertGreater(m_box["width"], 0)
            self.assertGreater(m_box["height"], 0)

            # 3. Interactive control >= MIN_TOUCH_TARGET_PX
            connect_btn = page.locator('[data-testid="connect-button"]')
            self.assertTrue(connect_btn.is_visible(), "Mobile connect button must be visible")
            b_box = connect_btn.bounding_box()
            self.assertIsNotNone(b_box)
            self.assertGreaterEqual(b_box["height"], MIN_TOUCH_TARGET_PX)
            self.assertGreaterEqual(b_box["width"], MIN_TOUCH_TARGET_PX)

            # 4. Mobile complete journey traversal
            start_btn = page.locator('[data-testid="start-handoff-button"]')
            self.assertTrue(start_btn.is_visible())
            start_btn.click()

            handoff_section = page.locator('[data-testid="handoff-phase"]')
            self.assertTrue(handoff_section.is_visible())
            enter_btn = page.locator('[data-testid="enter-practice-button"]')
            self.assertTrue(enter_btn.is_visible())
            enter_btn.click()

            practice_section = page.locator('[data-testid="practice-phase"]')
            self.assertTrue(practice_section.is_visible())
            text_input = page.locator('[data-testid="user-utterance-input"]')
            self.assertTrue(text_input.is_visible())
            text_input.fill("Mobile message to Alex.")
            send_btn = page.locator('[data-testid="send-turn-button"]')
            self.assertTrue(send_btn.is_visible())
            send_btn.click()

            feedback_nav_btn = page.locator('[data-testid="view-feedback-button"]')
            self.assertTrue(feedback_nav_btn.is_visible())
            feedback_nav_btn.click()

            feedback_section = page.locator('[data-testid="feedback-phase"]')
            self.assertTrue(feedback_section.is_visible())

            retry_btn = page.locator('[data-testid="retry-practice-button"]')
            self.assertTrue(retry_btn.is_visible())
            retry_btn.click()

            self.assertTrue(practice_section.is_visible())

            browser.close()

    def test_keyboard_only_traversal_and_activation(self):
        """
        Navigates and activates all essential controls using exclusively keyboard:
        Tab to focus, Space/Enter to activate.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport=DESKTOP_VIEWPORT)
            page.goto(self.base_url, wait_until="domcontentloaded")

            # Tab to consent checkbox and check with Space
            page.keyboard.press("Tab")
            consent_box = page.locator('[data-testid="consent-avatar-checkbox"]')
            self.assertTrue(consent_box.is_visible(), "Consent checkbox must be present for keyboard tab")
            is_active = consent_box.evaluate("el => el === document.activeElement")
            self.assertTrue(is_active, "Tab must focus consent checkbox")
            page.keyboard.press("Space")
            self.assertTrue(consent_box.is_checked(), "Space must check consent checkbox")

            # Tab to connect button and activate with Enter
            page.keyboard.press("Tab")
            connect_btn = page.locator('[data-testid="connect-button"]')
            self.assertTrue(connect_btn.is_visible(), "Connect button must be present for keyboard tab")
            is_btn_active = connect_btn.evaluate("el => el === document.activeElement")
            self.assertTrue(is_btn_active, "Tab must focus connect button")
            page.keyboard.press("Enter")

            # Tab to start handoff button and activate
            page.keyboard.press("Tab")
            start_btn = page.locator('[data-testid="start-handoff-button"]')
            self.assertTrue(start_btn.is_visible(), "Start handoff button must be present for keyboard tab")
            is_start_active = start_btn.evaluate("el => el === document.activeElement")
            self.assertTrue(is_start_active, "Tab must focus start handoff button")
            page.keyboard.press("Enter")

            browser.close()

    def test_microphone_permission_denial_fallback_to_text(self):
        """
        Exercises the actual permission request path.
        When microphone permission is denied, UI falls back cleanly to the text practice floor.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport=DESKTOP_VIEWPORT, permissions=[])
            page = context.new_page()
            page.goto(self.base_url, wait_until="domcontentloaded")

            mic_btn = page.locator('[data-testid="mic-toggle-button"]')
            self.assertTrue(mic_btn.is_visible(), "Mic toggle button must be visible")
            mic_btn.click()

            text_floor = page.locator('[data-testid="user-utterance-input"]')
            self.assertTrue(text_floor.is_visible(), "Text floor input must remain active when mic is denied")

            denial_notice = page.locator('[data-testid="mic-denied-notice"]')
            self.assertTrue(denial_notice.is_visible(), "Mic denial feedback must be shown to the user")

            browser.close()

    def test_slow_network_single_flight_submission_and_stable_ui(self):
        """
        Simulates slow network conditions by introducing delay on turn route.
        Proves exactly one submission, one committed turn, stable sequence, and no duplicate.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport=DESKTOP_VIEWPORT)

            turn_calls = []

            def handle_turn(route):
                turn_calls.append(route.request.post_data)
                time.sleep(0.5)
                route.continue_()

            page.route("**/api/rehearsal/sessions/*/turn", handle_turn)
            page.goto(self.base_url, wait_until="domcontentloaded")

            input_box = page.locator('[data-testid="user-utterance-input"]')
            self.assertTrue(input_box.is_visible(), "Input box must be visible")
            input_box.fill("Slow network turn message.")

            send_btn = page.locator('[data-testid="send-turn-button"]')
            self.assertTrue(send_btn.is_visible(), "Send button must be visible")
            send_btn.click()

            # Second rapid click must be disabled or ignored
            send_btn.click()

            turn_bubbles = page.locator('[data-testid="turn-bubble"]')
            self.assertEqual(len(turn_calls), 1, "Only one turn request must be dispatched across flight")
            self.assertEqual(turn_bubbles.count(), 1, "UI must render exactly one committed turn bubble")

            browser.close()


if __name__ == "__main__":
    unittest.main()
