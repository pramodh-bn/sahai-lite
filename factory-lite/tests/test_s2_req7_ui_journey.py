"""Stage 2: the spec implies an end-user UI ("stand-in demonstration ->
Take My Seat -> practice -> feedback -> retry" -- MASTER_PROMPT.md: "User
watches a stand-in model a negotiation, takes their seat, practices...").
This is the real-browser, black-box journey test for that flow, using
Playwright per the Verifier mandate ("Playwright real browser journeys").

Contract convention (see CONTRACT.md): the Stage 1 app serves the Stage 2
UI at the documented base URL's "/" root (same host:port as app/RUN.md's
Health URL, with the /health suffix dropped). Required `data-testid`
hooks, one screen per rehearsal state:

  [data-testid="start-demo"]       -- visible in the "demo" screen; click to advance to take_my_seat
  [data-testid="take-my-seat"]     -- visible once in take_my_seat; click to advance to practice
  [data-testid="practice-input"]   -- a text input, visible in practice
  [data-testid="send-utterance"]   -- click to submit practice-input's value
  [data-testid="feedback-score"]   -- visible in feedback; text content is the evidence score
  [data-testid="retry-button"]     -- visible in feedback; click to retry (new attempt, back to practice)

A screenshot is captured after every step (pass or fail) under
factory-lite/tests/evidence/screenshots/ -- UI chrome only, no secrets,
and only ever against the localhost URL enforced by s2_helpers.
"""
import unittest
from pathlib import Path

from s2_helpers import AppProcess, app_base_url

SCREENSHOT_DIR = Path(__file__).resolve().parent / "evidence" / "screenshots"


class TestRehearsalUiJourney(unittest.TestCase):
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
                "install with `pip install playwright && playwright install chromium` to run this journey"
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
        self.page = self.browser.new_page()
        self._step = 0

    def tearDown(self):
        self.page.close()

    def _snapshot(self, label):
        self._step += 1
        path = SCREENSHOT_DIR / f"{self.id().split('.')[-1]}_{self._step:02d}_{label}.png"
        try:
            self.page.screenshot(path=str(path))
        except Exception:
            pass  # best-effort; never let screenshotting mask the real assertion failure

    def test_full_demo_to_retry_journey(self):
        self.page.goto(app_base_url() + "/")
        self._snapshot("landing")

        self.page.click('[data-testid="start-demo"]')
        self._snapshot("after_start_demo")

        self.page.click('[data-testid="take-my-seat"]')
        self._snapshot("after_take_my_seat")

        self.page.fill('[data-testid="practice-input"]', "What is your budget for this?")
        self.page.click('[data-testid="send-utterance"]')
        self._snapshot("after_first_utterance")

        self.page.click('[data-testid="send-utterance"]')  # end the attempt / move to feedback, per contract
        self._snapshot("after_feedback_request")

        score_el = self.page.locator('[data-testid="feedback-score"]')
        score_el.wait_for(state="visible", timeout=5000)
        score_text = score_el.text_content()
        self.assertTrue(score_text and score_text.strip(), "feedback screen showed no evidence score")
        self._snapshot("feedback_shown")

        self.page.click('[data-testid="retry-button"]')
        self._snapshot("after_retry")

        practice_input = self.page.locator('[data-testid="practice-input"]')
        practice_input.wait_for(state="visible", timeout=5000)
        self.assertEqual(
            practice_input.input_value(), "",
            "retry did not return to a fresh practice input at the pivot",
        )


if __name__ == "__main__":
    unittest.main()
