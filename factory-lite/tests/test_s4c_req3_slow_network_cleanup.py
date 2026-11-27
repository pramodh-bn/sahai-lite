"""Stage 4C requirement 3: slow-network honesty and cleanup observability.

A locally delayed practice response must show a thinking indicator, disable
send, and still commit exactly one turn. End-and-delete in the browser must
issue the application DELETE, show a deletion status, leave the session
unreadable, and stay idempotent.

Contract: ``factory-lite/docs/stage-4c-acceptance-contract.md`` sections 6-7.
"""
import time
import unittest

from s4c_helpers import (
    api_get_json,
    assert_hidden,
    assert_visible,
    click,
    goto_home,
    is_visible,
    new_context,
    start_app,
    to_practice,
)


class TestSlowNetworkAndCleanup(unittest.TestCase):
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
        self.context = new_context(self.browser, "desktop")
        self.page = self.context.new_page()
        goto_home(self.page)

    def tearDown(self):
        self.page.close()
        self.context.close()

    def test_slow_practice_shows_thinking_and_commits_exactly_one_turn(self):
        delay_ms = 800

        def slow(route):
            time.sleep(delay_ms / 1000.0)
            route.continue_()

        self.page.route("**/api/rehearsal/sessions/*/practice", slow)
        sid = to_practice(self.page)
        self.assertTrue(sid, "the page did not create a session before practice")

        self.page.locator('[data-testid="practice-input"]').fill("How flexible are the terms?")
        click(self.page, '[data-testid="send-utterance"]', "send control is not available")

        assert_visible(self.page, '[data-testid="thinking-indicator"]',
                       "no thinking indicator is shown while a slow turn is in flight", timeout=3000)
        self.assertTrue(self.page.locator('[data-testid="send-utterance"]').is_disabled(),
                        "send is still enabled while a turn is in flight")

        assert_hidden(self.page, '[data-testid="thinking-indicator"]',
                      "thinking indicator never cleared after the slow turn", timeout=10000)

        status, snap = api_get_json(f"/api/rehearsal/sessions/{sid}")
        self.assertEqual(status, 200, f"session snapshot failed: {status} {snap}")
        user_turns = [t for t in snap.get("transcript", []) if t.get("speaker") == "user"]
        self.assertEqual(len(user_turns), 1,
                         f"slow response double-committed turns: {user_turns}")

    def test_end_and_delete_deletes_session_and_is_idempotent(self):
        sid = to_practice(self.page)
        self.assertTrue(sid, "the page did not create a session before practice")

        with self.page.expect_response(
            lambda r: r.request.method == "DELETE" and r.url.rstrip("/").endswith(sid),
            timeout=15000,
        ) as info:
            click(self.page, '[data-testid="end-and-delete"]',
                  "end-and-delete is not available in practice")
        status = info.value.status
        self.assertIn(status, (200, 204),
                      f"DELETE from the browser returned {status}, expected 200/204")

        assert_visible(self.page, '[data-testid="cleanup-status"]',
                       "cleanup status was not shown after deletion")
        text = self.page.locator('[data-testid="cleanup-status"]').text_content().lower()
        self.assertIn("delet", text, f"cleanup status does not report deletion: {text!r}")

        status, body = api_get_json(f"/api/rehearsal/sessions/{sid}")
        self.assertEqual(status, 404, f"session still readable after delete: {status} {body}")

        if is_visible(self.page, '[data-testid="end-and-delete"]'):
            with self.page.expect_response(
                lambda r: r.request.method == "DELETE" and r.url.rstrip("/").endswith(sid),
                timeout=15000,
            ) as second:
                click(self.page, '[data-testid="end-and-delete"]')
            self.assertLess(second.value.status, 500,
                            f"second delete returned {second.value.status}")
        body_text = self.page.locator("body").text_content()
        self.assertNotIn("HTTP 500", body_text, "the page surfaced a server error after cleanup")


if __name__ == "__main__":
    unittest.main()
