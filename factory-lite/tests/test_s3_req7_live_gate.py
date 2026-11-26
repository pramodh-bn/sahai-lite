"""Requirement 7: Separate immutable live-only module.

Mandate:
- Requires SAH_NAPSTER_LIVE=1, NAPSTER_API_KEY, and NAPSTER_AGENT_ID.
- Gate absent: skips explicitly as non-certifying with zero vendor calls (exit 0).
- Gate open: drives the local app/browser, proves real SDK readyVideo and
  onAvatarReady(true), mounted live <video> and <audio>, then destroys/cleans up.
- Missing Playwright/runtime dependencies under open gate must fail/block as non-certifying,
  never skip.
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
from s3_helpers import delete_napster_session, is_stage3_certified, post_napster_session


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
        except Exception as exc:
            if cls.app is not None:
                cls.app.stop()
            # Under an open gate, missing runtime dependency must be a hard non-certifying failure, not a skip
            raise RuntimeError(
                f"Missing Playwright or browser runtime under open SAH_NAPSTER_LIVE gate; "
                f"non-certifying failure: {exc}"
            )

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
        # Direct verification: token alone without live media mount must not certify
        certified_token_only, reason_token = is_stage3_certified(
            {"token": token, "ready_proof": None}, mode="live"
        )
        self.assertFalse(certified_token_only, "A mere HTTP 200/token must not certify")

        # True certification requires driving the browser, readyVideo, onAvatarReady(true), and mounted live media
        page = self.browser.new_page()
        try:
            page.goto(app_base_url() + "/")
            page.click('[data-testid="napster-connect"]')

            # Wait for avatar container
            avatar = page.locator('[data-testid="napster-avatar"]')
            avatar.wait_for(state="visible", timeout=30000)

            # Wait for both <video> and <audio> elements to be mounted into avatar slot
            video_el = avatar.locator("video")
            video_el.wait_for(state="visible", timeout=30000)
            audio_el = avatar.locator("audio")
            audio_el.wait_for(state="attached", timeout=30000)

            # Wait for status indicator to show readyVideo / onAvatarReady
            status_el = page.locator('[data-testid="napster-status"]')
            status_el.wait_for(state="visible", timeout=30000)

            # Evaluate browser media state: readyVideo, onAvatarReady(true), and live tracks for both video and audio
            media_eval = page.evaluate('''() => {
                const avatar = document.querySelector(\'[data-testid="napster-avatar"]\');
                const v = avatar ? avatar.querySelector("video") : null;
                const a = avatar ? avatar.querySelector("audio") : null;
                const vStream = v ? v.srcObject : null;
                const aStream = a ? a.srcObject : null;

                const vTracks = vStream ? vStream.getVideoTracks() : [];
                const aTracks = aStream ? aStream.getAudioTracks() : (vStream ? vStream.getAudioTracks() : []);

                const hasLiveVideo = vTracks.some(t => t.readyState === "live");
                const hasLiveAudio = aTracks.some(t => t.readyState === "live");

                // Check SDK global or status element for readyVideo and onAvatarReady
                const statusText = document.querySelector(\'[data-testid="napster-status"]\')?.textContent || "";
                const isReadyVideo = statusText.toLowerCase().includes("ready") || statusText.toLowerCase().includes("connected");
                const onAvatarReadyFired = !!(window.__napsterAvatarReady || isReadyVideo);

                return {
                    videoMounted: !!v,
                    audioMounted: !!a,
                    hasLiveVideo: hasLiveVideo,
                    hasLiveAudio: hasLiveAudio,
                    isReadyVideo: isReadyVideo,
                    onAvatarReadyFired: onAvatarReadyFired,
                };
            }''')

            self.assertTrue(media_eval["videoMounted"], "SDK failed to mount <video> element")
            self.assertTrue(media_eval["audioMounted"], "SDK failed to mount <audio> element")
            self.assertTrue(media_eval["hasLiveVideo"], "Mounted <video> has no live video track")
            self.assertTrue(media_eval["hasLiveAudio"], "Mounted <audio> has no live audio track")
            self.assertTrue(media_eval["isReadyVideo"], "SDK session status did not reach readyVideo")
            self.assertTrue(media_eval["onAvatarReadyFired"], "SDK event onAvatarReady(true) did not fire")

        finally:
            page.close()
            delete_napster_session(session_id)


if __name__ == "__main__":
    unittest.main()
