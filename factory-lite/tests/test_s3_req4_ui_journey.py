"""Requirement 4 & 5: End-user UI journey with opt-in Napster avatar and mic fallback.

Contract conventions:
- The UI extends Stage 2 journey at `/` (same documented Health URL base).
- Hooks per screen/state:
    [data-testid="start-demo"]          -- start demonstration
    [data-testid="napster-connect"]     -- explicit opt-in button to connect live Napster avatar
    [data-testid="napster-avatar"]      -- slot where WebRTC video/audio avatar mounts
    [data-testid="napster-status"]      -- status indicator ("disconnected", "connecting", "connected", "fallback")
    [data-testid="take-my-seat"]        -- advance to practice
    [data-testid="mic-denied-fallback"] -- visible notice when microphone access is denied
    [data-testid="practice-input"]      -- text input, remains usable even when mic is denied
    [data-testid="send-utterance"]      -- submit text practice utterance
    [data-testid="feedback-score"]      -- feedback score element
    [data-testid="retry-button"]        -- retry button
    [data-testid="napster-disconnect"]  -- explicit cleanup/disconnect button
"""
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

import unittest
from pathlib import Path

from s2_helpers import AppProcess, app_base_url

SCREENSHOT_DIR = Path(__file__).resolve().parent / "evidence" / "screenshots"


class TestStage3UiEmbodiedJourney(unittest.TestCase):
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
            raise unittest.SkipTest(
                f"playwright not installed in this environment ({exc}); "
                "install with `pip install playwright && playwright install chromium`"
            )
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
        self.context = self.browser.new_context(permissions=[])  # Deny microphone permission
        self.page = self.context.new_page()
        self._step = 0

    def tearDown(self):
        self.page.close()
        self.context.close()

    def _snapshot(self, label):
        self._step += 1
        path = SCREENSHOT_DIR / f"{self.id().split('.')[-1]}_{self._step:02d}_{label}.png"
        try:
            self.page.screenshot(path=str(path))
        except Exception:
            pass

    def test_full_embodied_journey_with_opt_in_and_mic_fallback(self):
        self.page.goto(app_base_url() + "/")
        self._snapshot("s3_landing")

        # 1. Demo state: verify opt-in connect button is visible and avatar slot exists
        connect_btn = self.page.locator('[data-testid="napster-connect"]')
        connect_btn.wait_for(state="visible", timeout=5000)
        avatar_slot = self.page.locator('[data-testid="napster-avatar"]')
        self.assertTrue(avatar_slot.is_visible(), "Napster avatar slot not visible")

        status_el = self.page.locator('[data-testid="napster-status"]')
        self.assertTrue(status_el.is_visible(), "Napster status element not visible")
        self._snapshot("s3_demo_opt_in_visible")

        # 2. Click opt-in connect
        connect_btn.click()
        self._snapshot("s3_after_opt_in_click")

        # In offline/mock mode, status must honestly report offline/fallback or unavailable
        status_text = status_el.text_content().lower()
        self.assertTrue(
            any(w in status_text for w in ("offline", "fallback", "unavailable", "disconnected", "connecting")),
            f"Status must display honest state: {status_text}",
        )

        # 3. Advance to take_my_seat
        self.page.click('[data-testid="start-demo"]')
        self._snapshot("s3_after_start_demo")

        self.page.click('[data-testid="take-my-seat"]')
        self._snapshot("s3_after_take_my_seat")

        # 4. In practice state: microphone is denied, verify fallback notice is visible
        mic_fallback = self.page.locator('[data-testid="mic-denied-fallback"]')
        mic_fallback.wait_for(state="visible", timeout=5000)
        self._snapshot("s3_mic_denied_fallback_visible")

        # 5. Text practice remains usable
        self.page.fill('[data-testid="practice-input"]', "Can we discuss sign-on flexibility?")
        self.page.click('[data-testid="send-utterance"]')
        self._snapshot("s3_text_practice_utterance")

        # End practice and verify feedback
        self.page.click('[data-testid="send-utterance"]')
        score_el = self.page.locator('[data-testid="feedback-score"]')
        score_el.wait_for(state="visible", timeout=5000)
        self._snapshot("s3_feedback_shown")

        # 6. Retry returns to practice
        self.page.click('[data-testid="retry-button"]')
        self._snapshot("s3_after_retry")

        # 7. Disconnect / cleanup if disconnect button exists
        disconnect_btn = self.page.locator('[data-testid="napster-disconnect"]')
        if disconnect_btn.is_visible():
            disconnect_btn.click()
            self._snapshot("s3_after_disconnect")


if __name__ == "__main__":
    unittest.main()
