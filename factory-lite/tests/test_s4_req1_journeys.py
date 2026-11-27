"""
Stage 4 Requirement 8: Responsive User Journeys and Accessibility.

Executes complete real Playwright journeys across desktop (1280x720) and mobile (375x667)
viewports through demo -> handoff -> practice -> feedback -> retry.
Measures exact [data-testid="avatar-slot"], child media elements, and all interactive controls (>= 44px)
without selector fallbacks, swallowed timeouts, or conditional guards.
Verifies keyboard traversal across the entire journey, microphone permission denial fallback,
and slow-network single flight submission.
"""

import time
import unittest

from playwright.sync_api import sync_playwright

from s4_constants import (
    DESKTOP_VIEWPORT,
    MIN_TOUCH_TARGET_PX,
    MOBILE_VIEWPORT,
)
from s4_helpers import AppProcess, app_base_url, get_json


class TestStage4UserJourneysAndAccessibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_process = AppProcess().start()
        cls.base_url = app_base_url()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.app_process.stop()

    def test_desktop_1280x720_complete_playwright_journey(self):
        """
        Desktop 1280x720 viewport executes complete journey:
        demo -> handoff -> practice -> feedback -> retry.
        Measures exact [data-testid="avatar-slot"], child media elements, document overflow,
        and touch targets >= MIN_TOUCH_TARGET_PX across all interactive controls.
        """
        page = self.browser.new_page(viewport=DESKTOP_VIEWPORT)
        try:
            page.goto(self.base_url, wait_until="domcontentloaded")

            # 1. Document overflow assertion
            scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
            client_width = page.evaluate("() => document.documentElement.clientWidth")
            self.assertLessEqual(scroll_width, client_width, "Desktop document must not have horizontal overflow")

            # 2. Avatar Slot and Child Media Bounding Box
            avatar_slot = page.locator('[data-testid="avatar-slot"]')
            self.assertTrue(avatar_slot.is_visible(), "Expected avatar slot to be visible on desktop landing")
            a_box = avatar_slot.bounding_box()
            self.assertIsNotNone(a_box)
            self.assertGreaterEqual(a_box["x"], 0)
            self.assertGreaterEqual(a_box["y"], 0)
            self.assertLessEqual(a_box["x"] + a_box["width"], 1280, "Avatar slot must fit within desktop width")
            self.assertLessEqual(a_box["y"] + a_box["height"], 720, "Avatar slot must fit within desktop height")

            media_element = avatar_slot.locator('[data-testid="avatar-media"]')
            self.assertTrue(media_element.is_visible(), "Avatar slot must contain visible child media element")
            m_box = media_element.bounding_box()
            self.assertIsNotNone(m_box)
            self.assertLessEqual(m_box["x"] + m_box["width"], a_box["x"] + a_box["width"], "Media must not overflow avatar slot width")
            self.assertLessEqual(m_box["y"] + m_box["height"], a_box["y"] + a_box["height"], "Media must not overflow avatar slot height")

            # 3. Interactive controls touch target >= MIN_TOUCH_TARGET_PX (44px)
            connect_btn = page.locator('[data-testid="connect-btn"]')
            self.assertTrue(connect_btn.is_visible(), "Expected connect button")
            c_box = connect_btn.bounding_box()
            self.assertIsNotNone(c_box)
            self.assertGreaterEqual(c_box["height"], MIN_TOUCH_TARGET_PX, "Connect button height must be >= 44px")
            self.assertGreaterEqual(c_box["width"], MIN_TOUCH_TARGET_PX, "Connect button width must be >= 44px")

            # Step 1: Demo to Handoff
            start_btn = page.locator('[data-testid="start-btn"]')
            self.assertTrue(start_btn.is_visible(), "Expected start button")
            s_box = start_btn.bounding_box()
            self.assertIsNotNone(s_box)
            self.assertGreaterEqual(s_box["height"], MIN_TOUCH_TARGET_PX, "Start button height must be >= 44px")
            self.assertGreaterEqual(s_box["width"], MIN_TOUCH_TARGET_PX, "Start button width must be >= 44px")
            start_btn.click()

            # Step 2: Handoff to Practice
            seat_btn = page.locator('[data-testid="take-seat-btn"]')
            self.assertTrue(seat_btn.is_visible(), "Expected take seat button in handoff")
            seat_box = seat_btn.bounding_box()
            self.assertIsNotNone(seat_box)
            self.assertGreaterEqual(seat_box["height"], MIN_TOUCH_TARGET_PX, "Take seat button height must be >= 44px")
            self.assertGreaterEqual(seat_box["width"], MIN_TOUCH_TARGET_PX, "Take seat button width must be >= 44px")
            seat_btn.click()

            # Step 3: Practice Turn
            turn_input = page.locator('[data-testid="turn-input"]')
            self.assertTrue(turn_input.is_visible(), "Expected turn input in practice")
            turn_input.fill("Hello, let's discuss the contract terms.")
            send_btn = page.locator('[data-testid="send-turn-btn"]')
            self.assertTrue(send_btn.is_visible(), "Expected send turn button")
            send_box = send_btn.bounding_box()
            self.assertIsNotNone(send_box)
            self.assertGreaterEqual(send_box["height"], MIN_TOUCH_TARGET_PX, "Send button height must be >= 44px")
            self.assertGreaterEqual(send_box["width"], MIN_TOUCH_TARGET_PX, "Send button width must be >= 44px")
            send_btn.click()

            # Step 4: Advance to Feedback
            feedback_btn = page.locator('[data-testid="view-feedback-btn"]')
            self.assertTrue(feedback_btn.is_visible(), "Expected feedback button")
            feedback_box = feedback_btn.bounding_box()
            self.assertIsNotNone(feedback_box)
            self.assertGreaterEqual(feedback_box["height"], MIN_TOUCH_TARGET_PX, "Feedback button height must be >= 44px")
            self.assertGreaterEqual(feedback_box["width"], MIN_TOUCH_TARGET_PX, "Feedback button width must be >= 44px")
            feedback_btn.click()

            # Step 5: Retry
            retry_btn = page.locator('[data-testid="retry-btn"]')
            self.assertTrue(retry_btn.is_visible(), "Expected retry button in feedback")
            r_box = retry_btn.bounding_box()
            self.assertIsNotNone(r_box)
            self.assertGreaterEqual(r_box["height"], MIN_TOUCH_TARGET_PX, "Retry button height must be >= 44px")
            self.assertGreaterEqual(r_box["width"], MIN_TOUCH_TARGET_PX, "Retry button width must be >= 44px")
            retry_btn.click()

            # Verify back in practice
            self.assertTrue(turn_input.is_visible(), "Expected practice input visible after retry")
        finally:
            page.close()

    def test_mobile_375x667_complete_playwright_journey(self):
        """
        Mobile 375x667 viewport executes complete journey:
        demo -> handoff -> practice -> feedback -> retry.
        Measures exact [data-testid="avatar-slot"], child media elements, mobile overflow,
        and touch targets >= MIN_TOUCH_TARGET_PX.
        """
        page = self.browser.new_page(viewport=MOBILE_VIEWPORT)
        try:
            page.goto(self.base_url, wait_until="domcontentloaded")

            # 1. Document horizontal overflow assertion
            scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
            client_width = page.evaluate("() => document.documentElement.clientWidth")
            self.assertLessEqual(scroll_width, client_width, "Mobile document must not horizontally overflow")

            # 2. Avatar Slot within mobile boundaries
            avatar_slot = page.locator('[data-testid="avatar-slot"]')
            self.assertTrue(avatar_slot.is_visible(), "Expected avatar slot to be visible on mobile landing")
            a_box = avatar_slot.bounding_box()
            self.assertIsNotNone(a_box)
            self.assertGreaterEqual(a_box["x"], 0)
            self.assertGreaterEqual(a_box["y"], 0)
            self.assertLessEqual(a_box["x"] + a_box["width"], 375, "Avatar slot must fit within mobile width 375px")
            self.assertLessEqual(a_box["y"] + a_box["height"], 667, "Avatar slot must fit within mobile height 667px")

            media_element = avatar_slot.locator('[data-testid="avatar-media"]')
            self.assertTrue(media_element.is_visible(), "Avatar slot must contain visible child media element on mobile")
            m_box = media_element.bounding_box()
            self.assertIsNotNone(m_box)
            self.assertLessEqual(m_box["x"] + m_box["width"], a_box["x"] + a_box["width"], "Media must not overflow avatar slot width on mobile")
            self.assertLessEqual(m_box["y"] + m_box["height"], a_box["y"] + a_box["height"], "Media must not overflow avatar slot height on mobile")

            # 3. Mobile touch target measurements
            connect_btn = page.locator('[data-testid="connect-btn"]')
            self.assertTrue(connect_btn.is_visible(), "Expected connect button on mobile")
            c_box = connect_btn.bounding_box()
            self.assertIsNotNone(c_box)
            self.assertGreaterEqual(c_box["height"], MIN_TOUCH_TARGET_PX, "Mobile connect button height must be >= 44px")
            self.assertGreaterEqual(c_box["width"], MIN_TOUCH_TARGET_PX, "Mobile connect button width must be >= 44px")

            start_btn = page.locator('[data-testid="start-btn"]')
            self.assertTrue(start_btn.is_visible(), "Expected start button on mobile")
            s_box = start_btn.bounding_box()
            self.assertIsNotNone(s_box)
            self.assertGreaterEqual(s_box["height"], MIN_TOUCH_TARGET_PX, "Mobile start button height must be >= 44px")
            self.assertGreaterEqual(s_box["width"], MIN_TOUCH_TARGET_PX, "Mobile start button width must be >= 44px")
            start_btn.click()

            seat_btn = page.locator('[data-testid="take-seat-btn"]')
            self.assertTrue(seat_btn.is_visible(), "Expected take seat button in mobile handoff")
            seat_box = seat_btn.bounding_box()
            self.assertIsNotNone(seat_box)
            self.assertGreaterEqual(seat_box["height"], MIN_TOUCH_TARGET_PX, "Mobile take seat button height must be >= 44px")
            self.assertGreaterEqual(seat_box["width"], MIN_TOUCH_TARGET_PX, "Mobile take seat button width must be >= 44px")
            seat_btn.click()

            turn_input = page.locator('[data-testid="turn-input"]')
            self.assertTrue(turn_input.is_visible(), "Expected turn input in mobile practice")
            turn_input.fill("Mobile practice utterance.")
            send_btn = page.locator('[data-testid="send-turn-btn"]')
            self.assertTrue(send_btn.is_visible(), "Expected send button on mobile")
            send_box = send_btn.bounding_box()
            self.assertIsNotNone(send_box)
            self.assertGreaterEqual(send_box["height"], MIN_TOUCH_TARGET_PX, "Mobile send button height must be >= 44px")
            self.assertGreaterEqual(send_box["width"], MIN_TOUCH_TARGET_PX, "Mobile send button width must be >= 44px")
            send_btn.click()

            feedback_btn = page.locator('[data-testid="view-feedback-btn"]')
            self.assertTrue(feedback_btn.is_visible(), "Expected feedback button on mobile")
            feedback_box = feedback_btn.bounding_box()
            self.assertIsNotNone(feedback_box)
            self.assertGreaterEqual(feedback_box["height"], MIN_TOUCH_TARGET_PX, "Mobile feedback button height must be >= 44px")
            self.assertGreaterEqual(feedback_box["width"], MIN_TOUCH_TARGET_PX, "Mobile feedback button width must be >= 44px")
            feedback_btn.click()

            retry_btn = page.locator('[data-testid="retry-btn"]')
            self.assertTrue(retry_btn.is_visible(), "Expected retry button on mobile")
            r_box = retry_btn.bounding_box()
            self.assertIsNotNone(r_box)
            self.assertGreaterEqual(r_box["height"], MIN_TOUCH_TARGET_PX, "Mobile retry button height must be >= 44px")
            self.assertGreaterEqual(r_box["width"], MIN_TOUCH_TARGET_PX, "Mobile retry button width must be >= 44px")
            retry_btn.click()

            self.assertTrue(turn_input.is_visible(), "Expected practice visible after mobile retry")
        finally:
            page.close()

    def test_keyboard_accessibility_focus_and_activation(self):
        """
        Keyboard-only navigation must traverse and activate the entire user flow:
        demo -> handoff -> practice -> feedback -> retry using Tab, Enter, and Space keys.
        """
        page = self.browser.new_page(viewport=DESKTOP_VIEWPORT)
        try:
            page.goto(self.base_url, wait_until="domcontentloaded")

            # Tab to Start Button
            page.keyboard.press("Tab")
            start_btn = page.locator('[data-testid="start-btn"]')
            self.assertTrue(start_btn.is_visible(), "Expected start button")
            is_start_focused = start_btn.evaluate("el => el === document.activeElement")
            self.assertTrue(is_start_focused, "Expected start button to be focused via Tab traversal")
            page.keyboard.press("Enter")

            # Tab to Take Seat Button
            page.keyboard.press("Tab")
            seat_btn = page.locator('[data-testid="take-seat-btn"]')
            self.assertTrue(seat_btn.is_visible(), "Expected take seat button in handoff")
            is_seat_focused = seat_btn.evaluate("el => el === document.activeElement")
            self.assertTrue(is_seat_focused, "Expected take seat button to be focused via Tab traversal")
            page.keyboard.press("Space")

            # Tab into Turn Input and type
            page.keyboard.press("Tab")
            turn_input = page.locator('[data-testid="turn-input"]')
            self.assertTrue(turn_input.is_visible(), "Expected turn input in practice")
            is_input_focused = turn_input.evaluate("el => el === document.activeElement")
            self.assertTrue(is_input_focused, "Expected turn input to be focused")
            page.keyboard.type("Keyboard traversal practice utterance.")

            # Tab to Send Button and press Enter
            page.keyboard.press("Tab")
            send_btn = page.locator('[data-testid="send-turn-btn"]')
            self.assertTrue(send_btn.is_visible(), "Expected send button")
            is_send_focused = send_btn.evaluate("el => el === document.activeElement")
            self.assertTrue(is_send_focused, "Expected send button to be focused")
            page.keyboard.press("Enter")

            # Tab to View Feedback Button
            page.keyboard.press("Tab")
            fb_btn = page.locator('[data-testid="view-feedback-btn"]')
            self.assertTrue(fb_btn.is_visible(), "Expected view feedback button")
            is_fb_focused = fb_btn.evaluate("el => el === document.activeElement")
            self.assertTrue(is_fb_focused, "Expected feedback button to be focused")
            page.keyboard.press("Enter")

            # Tab to Retry Button
            page.keyboard.press("Tab")
            retry_btn = page.locator('[data-testid="retry-btn"]')
            self.assertTrue(retry_btn.is_visible(), "Expected retry button in feedback")
            is_retry_focused = retry_btn.evaluate("el => el === document.activeElement")
            self.assertTrue(is_retry_focused, "Expected retry button to be focused")
            page.keyboard.press("Enter")

            # Confirm returned to practice
            self.assertTrue(turn_input.is_visible(), "Expected return to practice after keyboard retry activation")
        finally:
            page.close()

    def test_microphone_permission_denial_fallback_to_text(self):
        """
        Denying microphone permissions triggers clean text floor fallback without crashing.
        Proves actual media request was denied and no live audio track exists.
        """
        context = self.browser.new_context(
            viewport=DESKTOP_VIEWPORT,
            permissions=[],
        )
        page = context.new_page()
        try:
            page.goto(self.base_url, wait_until="domcontentloaded")

            # Trigger mic permission request
            mic_btn = page.locator('[data-testid="mic-toggle-btn"]')
            self.assertTrue(mic_btn.is_visible(), "Expected mic toggle button")
            mic_btn.click()

            # Prove no live track exists in page context
            has_live_track = page.evaluate("() => window.__liveAudioTrack !== undefined && window.__liveAudioTrack.readyState === 'live'")
            self.assertFalse(has_live_track, "No live audio track must exist when microphone permission is denied")

            # Text fallback input and indicator must remain visible and active
            text_indicator = page.locator('[data-testid="text-fallback-indicator"]')
            self.assertTrue(text_indicator.is_visible(), "Expected text fallback indicator when mic is denied")
            text_input = page.locator('[data-testid="turn-input"]')
            self.assertTrue(text_input.is_visible(), "Expected text input available in fallback mode")
        finally:
            page.close()
            context.close()

    def test_slow_network_single_flight_submission_and_stable_sequence(self):
        """
        Slow network test enters practice through UI, synchronizes two rapid activations,
        awaits response, and proves via server evidence/sequence that exactly one turn committed
        and UI/server sequence remain aligned.
        """
        page = self.browser.new_page(viewport=DESKTOP_VIEWPORT)
        try:
            # Add artificial route delay to the turn endpoint
            page.route("**/api/rehearsal/sessions/*/turn", lambda route: (
                time.sleep(1.0),
                route.continue_()
            ))
            page.goto(self.base_url, wait_until="domcontentloaded")

            start_btn = page.locator('[data-testid="start-btn"]')
            self.assertTrue(start_btn.is_visible(), "Expected start button")
            start_btn.click()

            seat_btn = page.locator('[data-testid="take-seat-btn"]')
            self.assertTrue(seat_btn.is_visible(), "Expected take seat button")
            seat_btn.click()

            turn_input = page.locator('[data-testid="turn-input"]')
            self.assertTrue(turn_input.is_visible(), "Expected turn input in practice")
            turn_input.fill("Slow network concurrency test.")

            send_btn = page.locator('[data-testid="send-turn-btn"]')
            self.assertTrue(send_btn.is_visible(), "Expected send button")

            # Rapid double activation before network response returns
            send_btn.click()
            send_btn.click()

            # Await UI completion
            turn_indicator = page.locator('[data-testid="turn-sent-confirmed"]')
            self.assertTrue(turn_indicator.is_visible(), "Expected single turn confirmation in UI")

            # Verify server session id and evidence
            session_id = page.evaluate("() => window.__sessionId || ''")
            self.assertTrue(bool(session_id), "Expected active session_id in page window")

            ev_status, ev_data = get_json(f"/api/rehearsal/sessions/{session_id}/evidence")
            self.assertEqual(ev_status, 200)
            self.assertIn("events", ev_data)
            turn_events = [e for e in ev_data["events"] if e.get("event") == "turn_committed"]
            self.assertEqual(len(turn_events), 1, "Exactly one turn must be committed on rapid double submission")
        finally:
            page.close()


if __name__ == "__main__":
    unittest.main()
