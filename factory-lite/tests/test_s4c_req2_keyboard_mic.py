"""Stage 4C requirement 2: keyboard-only operation and microphone denial.

The desktop journey is completed with Tab/Enter only, with a visible focus
indicator on the focused control. With microphone permission denied, the
fallback notice is shown, the recording indicator stays hidden, and text
practice still reaches feedback.

Contract: ``factory-lite/docs/stage-4c-acceptance-contract.md`` sections 4-5.
"""
import unittest

from s4c_helpers import (
    assert_hidden,
    assert_visible,
    focus_indicator,
    goto_home,
    new_context,
    start_app,
    viewport_meta_content,
)


class TestKeyboardAndMicrophone(unittest.TestCase):
    app = None
    playwright = None
    browser = None

    @classmethod
    def setUpClass(cls):
        cls.app = start_app()
        from playwright.sync_api import sync_playwright
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
        self.context = new_context(self.browser, "desktop")  # no microphone permission
        self.page = self.context.new_page()
        goto_home(self.page)

    def tearDown(self):
        self.page.close()
        self.context.close()

    def _focus_testid(self, testid, max_tabs=25):
        for _ in range(max_tabs):
            self.page.keyboard.press("Tab")
            current = self.page.evaluate(
                "() => document.activeElement ? document.activeElement.getAttribute('data-testid') : null"
            )
            if current == testid:
                return
        raise AssertionError(f"keyboard Tab never reached {testid!r} within {max_tabs} presses")

    def _activate(self, testid):
        self._focus_testid(testid)
        self.page.keyboard.press("Enter")

    def test_keyboard_only_journey_reaches_feedback_retry_and_cleanup(self):
        style = focus_indicator(self.page, '[data-testid="start-demo"]')
        visible_outline = (style["outlineStyle"] not in ("none", "")
                           and float(style["outlineWidth"].replace("px", "") or 0) >= 1)
        self.assertTrue(
            visible_outline or style["boxShadow"] not in ("none", ""),
            f"focused control has no visible focus indicator: {style}",
        )

        self._activate("start-demo")
        assert_visible(self.page, '[data-testid="take-my-seat"]', "keyboard start demo failed")
        self._activate("take-my-seat")
        assert_visible(self.page, '[data-testid="practice-input"]', "keyboard handoff failed")

        self._focus_testid("practice-input")
        self.page.keyboard.type("What budget range works for you?")
        self._activate("send-utterance")

        # Empty submit ends the attempt and opens feedback.
        self._focus_testid("practice-input")
        self.page.keyboard.press("Control+A")
        self.page.keyboard.press("Delete")
        self._activate("send-utterance")
        assert_visible(self.page, '[data-testid="feedback-score"]', "keyboard feedback failed")

        self._activate("retry-button")
        assert_visible(self.page, '[data-testid="practice-input"]', "keyboard retry failed")

        self._activate("end-and-delete")
        assert_visible(self.page, '[data-testid="cleanup-status"]',
                       "keyboard end-and-delete did not show cleanup status")

    def test_mic_denial_keeps_text_practice_and_hides_recording_indicator(self):
        self._activate("start-demo")
        self._activate("take-my-seat")
        assert_visible(self.page, '[data-testid="practice-input"]', "practice did not start")

        assert_visible(self.page, '[data-testid="mic-denied-fallback"]',
                       "microphone denial notice is missing")
        self.assertGreaterEqual(
            self.page.locator('[data-testid="recording-indicator"]').count(), 1,
            "the recording indicator hook is missing from the page",
        )
        assert_hidden(self.page, '[data-testid="recording-indicator"]',
                      "recording indicator is visible while the microphone is denied")

        self.page.locator('[data-testid="practice-input"]').fill("Text only, no microphone.")
        self.page.locator('[data-testid="send-utterance"]').click()
        self.assertGreaterEqual(self.page.locator('[data-testid="practice-input"]').count(), 1)
        self.page.locator('[data-testid="practice-input"]').fill("")
        self.page.locator('[data-testid="send-utterance"]').click()
        assert_visible(self.page, '[data-testid="feedback-score"]',
                       "text practice could not reach feedback after mic denial")


if __name__ == "__main__":
    unittest.main()
