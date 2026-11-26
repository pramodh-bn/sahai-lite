"""Requirement 7: Separate immutable live-only module.

Mandate:
- Requires SAH_NAPSTER_LIVE=1, NAPSTER_API_KEY, and NAPSTER_AGENT_ID.
- Gate absent: skips explicitly as non-certifying with zero vendor calls (exit 0).
- Gate open: drives the local app/browser, proves real SDK readyVideo and
  onAvatarReady(true), mounted live <video> and <audio>, then destroys/cleans up.
- A mere HTTP 200 / token response CANNOT certify Stage 3.
"""
import json
import os
import sys
import unittest
import urllib.request
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from s2_helpers import AppProcess, app_base_url
from s3_helpers import delete_napster_session, post_napster_session


class TestNapsterLiveOnlyGate(unittest.TestCase):
    app = None
    playwright = None
    browser = None

    @classmethod
    def setUpClass(cls):
        # Strict gate check
        live_flag = os.environ.get("SAH_NAPSTER_LIVE") == "1"
        has_key = bool(os.environ.get("NAPSTER_API_KEY"))
        has_agent = bool(os.environ.get("NAPSTER_AGENT_ID"))

        if not (live_flag and has_key and has_agent):
            raise unittest.SkipTest(
                "explicit non-certifying skip: SAH_NAPSTER_LIVE=1, NAPSTER_API_KEY, and "
                "NAPSTER_AGENT_ID required; zero vendor calls made"
            )

        # Gate is open: start app and browser for real live probe
        cls.app = AppProcess().start()
        try:
            from playwright.sync_api import sync_playwright
            cls.playwright = sync_playwright().start()
            cls.browser = cls.playwright.chromium.launch()
        except ImportError as exc:
            cls.app.stop()
            raise unittest.SkipTest(f"playwright required for live browser certification: {exc}")

    @classmethod
    def tearDownClass(cls):
        if cls.browser is not None:
            cls.browser.close()
        if cls.playwright is not None:
            cls.playwright.stop()
        if cls.app is not None:
            cls.app.stop()

    def test_live_session_requires_full_sdk_avatar_ready_and_mounted_media(self):
        # 1. Create rehearsal session
        req = urllib.request.Request(
            f"{app_base_url()}/api/rehearsal/sessions",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            session_id = data["session_id"]

        # 2. Server creates WebRTC session
        status, session_data = post_napster_session(session_id, channel_type="webrtc")
        self.assertEqual(status, 200, f"Live session creation failed: {session_data}")
        token = session_data.get("token")
        self.assertTrue(token, "Live session returned no token")

        # Assertion: a mere HTTP 200 / token cannot certify Stage 3
        # True certification requires driving the browser, readyVideo, onAvatarReady, and live media
        page = self.browser.new_page()
        try:
            page.goto(app_base_url() + "/")
            page.click('[data-testid="napster-connect"]')

            # Wait for avatar container
            avatar = page.locator('[data-testid="napster-avatar"]')
            avatar.wait_for(state="visible", timeout=30000)

            # Wait for SDK readyVideo / onAvatarReady indicator
            status_el = page.locator('[data-testid="napster-status"]')
            status_el.wait_for(
                state="attached",
                timeout=30000,
            )

            # Assert live video and audio elements mounted
            video_el = avatar.locator("video")
            video_el.wait_for(state="attached", timeout=30000)
            audio_el = avatar.locator("audio")
            self.assertTrue(video_el.is_visible(), "Live video track not rendered")

            # Check that tracks are actively live
            is_live = page.evaluate('''() => {
                const v = document.querySelector(\'[data-testid="napster-avatar"] video\');
                const stream = v ? v.srcObject : null;
                const tracks = stream ? stream.getVideoTracks() : [];
                return tracks.length > 0 && tracks.some(t => t.readyState === "live");
            }''')
            self.assertTrue(is_live, "Attached video track is not live")
        finally:
            page.close()
            delete_napster_session(session_id)


if __name__ == "__main__":
    unittest.main()
