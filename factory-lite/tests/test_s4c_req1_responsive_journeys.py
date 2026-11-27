"""Stage 4C requirement 1: responsive desktop and mobile journeys.

Two real Chromium viewports run the whole journey (landing -> demonstration ->
handoff -> practice -> feedback -> retry -> cleanup) and assert the responsive
rules at every step: viewport meta, no horizontal scrolling, a capped and
contained avatar region, and in-viewport controls.

Contract: ``factory-lite/docs/stage-4c-acceptance-contract.md`` section 2.
"""
import unittest

from s4c_helpers import (
    assert_visible,
    bounding_box,
    click,
    finish_attempt,
    goto_home,
    new_context,
    retry,
    scroll_widths,
    send_text,
    start_app,
    take_my_seat,
    viewport_meta_content,
)


class TestResponsiveJourneys(unittest.TestCase):
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
        self.context = None
        self.page = None

    def tearDown(self):
        if self.page is not None:
            self.page.close()
        if self.context is not None:
            self.context.close()

    def _open(self, viewport):
        self.context = new_context(self.browser, viewport)
        self.page = self.context.new_page()
        goto_home(self.page)

    def _assert_layout(self, label):
        widths = scroll_widths(self.page)
        self.assertLessEqual(
            widths["html"], widths["inner"] + 1,
            f"[{label}] horizontal overflow at document level: {widths}",
        )
        self.assertLessEqual(
            widths["body"], widths["inner"] + 1,
            f"[{label}] horizontal overflow on body: {widths}",
        )
        box = bounding_box(self.page, '[data-testid="napster-avatar"]')
        self.assertIsNotNone(box, f"[{label}] avatar slot has no layout box")
        self.assertGreaterEqual(box["x"], -1, f"[{label}] avatar starts outside the viewport: {box}")
        self.assertLessEqual(box["x"] + box["width"], widths["inner"] + 1,
                             f"[{label}] avatar overflows the viewport: {box}")
        self.assertLessEqual(box["height"], widths["innerHeight"] * 0.45,
                             f"[{label}] avatar region is not capped: {box}")

    def _assert_control_in_viewport(self, label, selector):
        box = bounding_box(self.page, selector)
        widths = scroll_widths(self.page)
        self.assertIsNotNone(box, f"[{label}] {selector} has no layout box")
        self.assertGreaterEqual(box["x"], -1, f"[{label}] {selector} starts off-screen: {box}")
        self.assertLessEqual(box["x"] + box["width"], widths["inner"] + 1,
                             f"[{label}] {selector} overflows horizontally: {box}")

    def _run_journey(self, viewport):
        self._open(viewport)
        meta = viewport_meta_content(self.page)
        self.assertIsNotNone(meta, f"[{viewport}] missing <meta name=viewport>")
        self.assertIn("width=device-width", meta.replace(" ", "").lower(),
                      f"[{viewport}] viewport meta does not scale to device width: {meta!r}")
        self._assert_layout(f"{viewport} landing")

        click(self.page, '[data-testid="start-demo"]', "start demo is not available")
        assert_visible(self.page, '[data-testid="take-my-seat"]', "demonstration did not open")
        self._assert_layout(f"{viewport} demonstration")

        take_my_seat(self.page)
        self._assert_control_in_viewport(f"{viewport} practice", '[data-testid="practice-input"]')
        self._assert_control_in_viewport(f"{viewport} practice", '[data-testid="send-utterance"]')
        self._assert_layout(f"{viewport} practice")

        send_text(self.page, "What would you need to see to move this forward?")
        finish_attempt(self.page)
        self._assert_control_in_viewport(f"{viewport} feedback", '[data-testid="retry-button"]')
        self._assert_layout(f"{viewport} feedback")

        retry(self.page)
        self._assert_control_in_viewport(f"{viewport} retry", '[data-testid="end-and-delete"]')
        self._assert_layout(f"{viewport} retry")

        click(self.page, '[data-testid="end-and-delete"]', "end-and-delete is not available")
        assert_visible(self.page, '[data-testid="cleanup-status"]',
                       f"[{viewport}] cleanup status was not shown")
        self._assert_layout(f"{viewport} cleanup")

    def test_desktop_journey_is_responsive_end_to_end(self):
        self._run_journey("desktop")

    def test_mobile_375x667_journey_is_responsive_end_to_end(self):
        self._run_journey("mobile")

    def test_avatar_region_is_capped_at_both_viewports(self):
        for viewport in ("desktop", "mobile"):
            self._open(viewport)
            meta = viewport_meta_content(self.page)
            self.assertIsNotNone(meta, f"[{viewport}] missing <meta name=viewport>")
            self.assertIn("width=device-width", meta.replace(" ", "").lower(),
                          f"[{viewport}] viewport meta does not scale to device width: {meta!r}")
            widths = scroll_widths(self.page)
            box = bounding_box(self.page, '[data-testid="napster-avatar"]')
            self.assertIsNotNone(box, f"[{viewport}] avatar slot has no layout box")
            self.assertLessEqual(box["height"], widths["innerHeight"] * 0.45,
                                 f"[{viewport}] avatar region exceeds 45% of viewport height: {box}")
            self.assertLessEqual(box["width"], widths["inner"] + 1,
                                 f"[{viewport}] avatar region is wider than the viewport: {box}")
            self.tearDown()
            self.setUp()


if __name__ == "__main__":
    unittest.main()
