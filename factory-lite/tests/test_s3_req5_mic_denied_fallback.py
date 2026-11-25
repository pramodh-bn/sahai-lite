"""Stage 3: "denied mic fallback."

Black-box Playwright check: when the browser denies microphone access
(the default in a fresh browser context that is never granted the
permission), the Stage 3 voice-practice UI must fall back to the existing
text-only practice path instead of breaking. Convention (see
CONTRACT.md): a data-testid="voice-practice-toggle" control requests the
microphone; on denial, a data-testid="mic-denied-fallback" message
appears while data-testid="practice-input" remains usable.

Reuses Stage 2's AppProcess/app_base_url helpers (imported, not modified)
since Stage 3's UI is served by the same app at "/". Only ever talks to
that same localhost URL (same no-external-call guarantee as Stage 2);
Playwright's browser denies the mic locally, no real microphone or vendor
call is involved.
"""
import unittest
from pathlib import Path

from s2_helpers import AppProcess, app_base_url

SCREENSHOT_DIR = Path(__file__).resolve().parent / "evidence" / "screenshots"


class TestMicDeniedFallback(unittest.TestCase):
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
            raise unittest.SkipTest(f"playwright not installed in this environment ({exc})")
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

    def test_voice_toggle_falls_back_to_text_practice_when_mic_denied(self):
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        context = self.browser.new_context()  # microphone permission is never granted here
        page = context.new_page()
        try:
            page.goto(app_base_url() + "/")
            page.click('[data-testid="start-demo"]')
            page.click('[data-testid="take-my-seat"]')
            page.click('[data-testid="voice-practice-toggle"]')

            fallback = page.locator('[data-testid="mic-denied-fallback"]')
            fallback.wait_for(state="visible", timeout=5000)

            practice_input = page.locator('[data-testid="practice-input"]')
            self.assertTrue(
                practice_input.is_visible(),
                "text practice input must remain usable after the microphone is denied",
            )
        finally:
            try:
                page.screenshot(path=str(SCREENSHOT_DIR / "s3_mic_denied_fallback.png"))
            except Exception:
                pass
            context.close()


if __name__ == "__main__":
    unittest.main()
