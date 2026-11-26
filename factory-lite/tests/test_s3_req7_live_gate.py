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
        live_flag = os.environ.get("SAH_NAPSTER_LIVE") == "1"
        has_key = bool(os.environ.get("NAPSTER_API_KEY"))
        has_agent = bool(os.environ.get("NAPSTER_AGENT_ID"))

        if not (live_flag and has_key and has_agent):
            raise unittest.SkipTest(
                "explicit non-certifying skip: SAH_NAPSTER_LIVE=1, NAPSTER_API_KEY, and "
                "NAPSTER_AGENT_ID required; zero vendor calls made"
            )

        cls.app = AppProcess().start()
        try:
            from playwright.sync_api import sync_playwright

            cls.playwright = sync_playwright().start()
            cls.browser = cls.playwright.chromium.launch()
        except Exception as exc:
            if cls.app is not None:
                cls.app.stop()
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
        req = urllib.request.Request(
            f"{app_base_url()}/api/rehearsal/sessions",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            session_id = data["session_id"]

        status, session_data = post_napster_session(session_id, channel_type="webrtc")
        self.assertEqual(status, 200, f"Live session creation failed: {session_data}")
        token = session_data.get("token")
        self.assertTrue(token, "Live session returned no token")

        certified_token_only, _ = is_stage3_certified(
            {"token": token, "ready_proof": None}, mode="live"
        )
        self.assertFalse(certified_token_only, "A mere HTTP 200/token must not certify")

        page = self.browser.new_page()
        try:
            page.goto(app_base_url() + "/")
            page.click('[data-testid="napster-connect"]')

            avatar = page.locator('[data-testid="napster-avatar"]')
            avatar.wait_for(state="visible", timeout=30000)

            video_el = avatar.locator("video")
            video_el.wait_for(state="visible", timeout=30000)
            audio_el = avatar.locator("audio")
            audio_el.wait_for(state="attached", timeout=30000)

            status_el = page.locator('[data-testid="napster-status"]')
            status_el.wait_for(state="visible", timeout=30000)

            media_eval = page.evaluate('''() => {
                const avatar = document.querySelector(\'[data-testid="napster-avatar"]\');
                const v = avatar ? avatar.querySelector("video") : null;
                const a = avatar ? avatar.querySelector("audio") : null;
                const vStream = v ? v.srcObject : null;
                const aStream = a ? a.srcObject : null;

                const vTracks = vStream ? vStream.getVideoTracks() : [];
                const aTracks = aStream ? aStream.getAudioTracks() : [];

                const hasLiveVideo = vTracks.length > 0 && vTracks.some(t => t.readyState === "live");
                const hasLiveAudioOnAudioElement = aTracks.length > 0 && aTracks.some(t => t.readyState === "live");

                const statusEl = document.querySelector(\'[data-testid="napster-status"]\');
                const exactSdkStatus = window.__napsterSdkStatus !== undefined
                    ? window.__napsterSdkStatus
                    : (statusEl ? statusEl.getAttribute("data-sdk-status") : null);

                const exactAvatarReadyArg = window.__napsterAvatarReady !== undefined
                    ? window.__napsterAvatarReady
                    : (statusEl && statusEl.getAttribute("data-avatar-ready") === "true");

                return {
                    videoMounted: !!v,
                    audioMounted: !!a,
                    hasLiveVideo: hasLiveVideo,
                    hasLiveAudioOnAudioElement: hasLiveAudioOnAudioElement,
                    exactSdkStatus: exactSdkStatus,
                    exactAvatarReadyArg: exactAvatarReadyArg,
                };
            }''')

            self.assertTrue(media_eval["videoMounted"], "SDK failed to mount <video> element")
            self.assertTrue(media_eval["audioMounted"], "SDK failed to mount <audio> element")
            self.assertTrue(media_eval["hasLiveVideo"], "Mounted <video> has no live video track")
            self.assertTrue(
                media_eval["hasLiveAudioOnAudioElement"],
                "Mounted <audio> element itself must own a live audio track (no video stream fallback)"
            )
            self.assertEqual(
                media_eval["exactSdkStatus"],
                "readyVideo",
                f"SDK status must be exact 'readyVideo', got {media_eval['exactSdkStatus']!r}"
            )
            self.assertIs(
                media_eval["exactAvatarReadyArg"],
                True,
                f"onAvatarReady callback payload must strictly be boolean True, got {media_eval['exactAvatarReadyArg']!r}"
            )
        finally:
            page.close()
            delete_napster_session(session_id)


if __name__ == "__main__":
    unittest.main()
