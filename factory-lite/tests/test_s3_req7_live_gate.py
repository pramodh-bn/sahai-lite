"""Requirement 7: Separate immutable live-only module.

Mandate:
- Requires SAH_NAPSTER_LIVE=1, NAPSTER_API_KEY, and NAPSTER_AGENT_ID.
- Gate absent: skips explicitly as non-certifying with zero vendor calls (exit 0) and creates no files.
- Gate open:
    * Single browser-owned flow without direct test preallocation.
    * In-memory observation of single session creation and /napster-session POST (no printing/storing of raw tokens/IDs).
    * Connection ID hashed immediately with SHA-256 for lowercase correlation hash; vendor path redacted as /public/agents/[REDACTED]/connections.
    * Proves real SDK readyVideo and onAvatarReady(true), mounted live <video> and <audio> with audio-element-owned live track.
    * Explicit disconnect click observing DELETE response with session_destroyed=true and proving released media resources.
    * Best-effort cleanup on failure paths using captured rehearsal session ID. Cleanup failure fails certification prominently.
    * Enforces bounded duration: at most 1 connection, 1 cleanup, no test retry, <= 30s active duration.
    * Validates evidence with validate_stage3_evidence and is_stage3_certified(mode=\'live\').
    * Atomically writes validated redacted JSON to SAH_STAGE3_EVIDENCE_PATH (missing/unwritable path is a hard non-certifying failure).
- A mere HTTP 200 / token response CANNOT certify Stage 3.
"""
import hashlib
import json
import os
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from s2_helpers import AppProcess, app_base_url
from s3_helpers import delete_napster_session, is_stage3_certified, validate_stage3_evidence


class TestNapsterLiveOnlyGate(unittest.TestCase):
    app = None
    playwright = None
    browser = None
    evidence_path = None

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

        evidence_path_str = os.environ.get("SAH_STAGE3_EVIDENCE_PATH", "").strip()
        if not evidence_path_str:
            raise RuntimeError(
                "Missing SAH_STAGE3_EVIDENCE_PATH under open live gate; non-certifying failure"
            )

        evidence_path = Path(evidence_path_str)
        try:
            evidence_path.parent.mkdir(parents=True, exist_ok=True)
            test_touch = evidence_path.parent / f".test_probe_{os.getpid()}"
            test_touch.write_text("ok", encoding="utf-8")
            test_touch.unlink()
        except Exception as exc:
            raise RuntimeError(
                f"Unwritable SAH_STAGE3_EVIDENCE_PATH ({evidence_path}): {exc}"
            )
        cls.evidence_path = evidence_path

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
        t0 = time.monotonic()
        start_time_utc = datetime.now(timezone.utc).isoformat()

        # Token / HTTP 200 alone cannot certify
        certified_token_only, _ = is_stage3_certified(
            {"token": "dummy", "ready_proof": None}, mode="live"
        )
        self.assertFalse(certified_token_only, "A mere HTTP 200/token must not certify")

        session_id_holder = {"session_id": None}
        conn_hash_holder = {"hash": None, "post_status": None}
        cleanup_holder = {"destroyed": False, "status_code": None}
        request_counts = {"post_connection": 0, "delete_connection": 0}

        page = self.browser.new_page()

        def on_response(response):
            url = response.url
            method = response.request.method
            if "/api/rehearsal/sessions" in url and method == "POST":
                if not (
                    url.endswith("/napster-session")
                    or "/advance" in url
                    or "/practice" in url
                    or "/feedback" in url
                    or "/retry" in url
                ):
                    try:
                        data = response.json()
                        if isinstance(data, dict) and "session_id" in data:
                            session_id_holder["session_id"] = data["session_id"]
                    except Exception:
                        pass
            elif "/napster-session" in url and method == "POST":
                request_counts["post_connection"] += 1
                conn_hash_holder["post_status"] = response.status
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        conn_id = data.get("connection_id")
                        if conn_id:
                            conn_hash_holder["hash"] = hashlib.sha256(
                                conn_id.encode("utf-8")
                            ).hexdigest().lower()
                except Exception:
                    pass
            elif "/napster-session" in url and method == "DELETE":
                request_counts["delete_connection"] += 1
                cleanup_holder["status_code"] = response.status
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        cleanup_holder["destroyed"] = (
                            data.get("status") == "destroyed"
                            and data.get("session_destroyed") is True
                        )
                except Exception:
                    pass

        page.on("response", on_response)

        try:
            page.goto(app_base_url() + "/")

            connect_btn = page.locator('[data-testid="napster-connect"]')
            connect_btn.wait_for(state="visible", timeout=10000)
            connect_btn.click()

            avatar = page.locator('[data-testid="napster-avatar"]')
            avatar.wait_for(state="visible", timeout=25000)

            video_el = avatar.locator("video")
            video_el.wait_for(state="visible", timeout=25000)
            audio_el = avatar.locator("audio")
            audio_el.wait_for(state="attached", timeout=25000)

            status_el = page.locator('[data-testid="napster-status"]')
            status_el.wait_for(state="visible", timeout=25000)

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
                "Mounted <audio> element itself must own a live audio track (no video stream fallback)",
            )
            self.assertEqual(
                media_eval["exactSdkStatus"],
                "readyVideo",
                f"SDK status must be exact \'readyVideo\', got {media_eval['exactSdkStatus']!r}",
            )
            self.assertIs(
                media_eval["exactAvatarReadyArg"],
                True,
                f"onAvatarReady callback payload must strictly be boolean True, got {media_eval['exactAvatarReadyArg']!r}",
            )

            disconnect_btn = page.locator('[data-testid="napster-disconnect"]')
            disconnect_btn.wait_for(state="visible", timeout=5000)
            disconnect_btn.click()

            page.wait_for_timeout(1000)
            self.assertTrue(
                cleanup_holder["destroyed"],
                f"DELETE response was not session_destroyed: {cleanup_holder}",
            )

            release_eval = page.evaluate('''() => {
                const avatar = document.querySelector(\'[data-testid="napster-avatar"]\');
                const v = avatar ? avatar.querySelector("video") : null;
                const a = avatar ? avatar.querySelector("audio") : null;
                const vStream = v ? v.srcObject : null;
                const aStream = a ? a.srcObject : null;

                const vLive = vStream && vStream.getVideoTracks ? vStream.getVideoTracks().some(t => t.readyState === "live") : false;
                const aLive = aStream && aStream.getAudioTracks ? aStream.getAudioTracks().some(t => t.readyState === "live") : false;

                const avatarReady = window.__napsterAvatarReady;
                const sdkStatus = window.__napsterSdkStatus;

                return {
                    noLiveVideoTracks: !vLive,
                    noLiveAudioTracks: !aLive,
                    elementsCleared: (!v || v.srcObject === null) && (!a || a.srcObject === null),
                    avatarReadyFalse: avatarReady === false,
                    sdkStatusUnavailable: sdkStatus === "unavailable",
                };
            }''')
            self.assertTrue(release_eval["noLiveVideoTracks"], "Video tracks still live after disconnect")
            self.assertTrue(release_eval["noLiveAudioTracks"], "Audio tracks still live after disconnect")
            self.assertTrue(release_eval["elementsCleared"], "Video/audio elements not cleared after disconnect")
            self.assertTrue(release_eval["avatarReadyFalse"], "Avatar ready not false after disconnect")
            self.assertTrue(release_eval["sdkStatusUnavailable"], "SDK status not unavailable after disconnect")

        finally:
            page.close()
            # Best-effort cleanup on failure paths using captured session ID
            if not cleanup_holder["destroyed"] and session_id_holder["session_id"]:
                status, res = delete_napster_session(session_id_holder["session_id"])
                if status != 200 or not res.get("session_destroyed"):
                    raise RuntimeError(
                        f"Cleanup failure for session {session_id_holder['session_id']}; failed certification: {res}"
                    )

        elapsed = time.monotonic() - t0
        self.assertLessEqual(
            elapsed,
            30.0,
            f"Live session exceeded 30-second budget: {elapsed:.2f}s",
        )
        self.assertEqual(
            request_counts["post_connection"],
            1,
            f"Expected exactly 1 connection create, got {request_counts['post_connection']}",
        )
        self.assertEqual(
            request_counts["delete_connection"],
            1,
            f"Expected exactly 1 cleanup delete, got {request_counts['delete_connection']}",
        )
        self.assertTrue(
            conn_hash_holder["hash"],
            "No correlation hash recorded from single connection",
        )

        end_time_utc = datetime.now(timezone.utc).isoformat()
        evidence = {
            "start_time_utc": start_time_utc,
            "end_time_utc": end_time_utc,
            "probe_correlation_hash": conn_hash_holder["hash"],
            "http_probe": {
                "host": "companion-api.napster.com",
                "path": "/public/agents/[REDACTED]/connections",
                "method": "POST",
                "status_code": conn_hash_holder["post_status"] or 200,
            },
            "ready_proof": {
                "event": "onAvatarReady",
                "avatar_ready": True,
                "status": "readyVideo",
            },
            "media_proof": {
                "video_mounted": True,
                "audio_mounted": True,
                "video_track_live": True,
                "audio_track_live": True,
            },
            "cleanup_proof": {
                "session_destroyed": True,
                "resources_released": True,
            },
            "redacted": True,
        }

        val_errors = validate_stage3_evidence(evidence)
        self.assertEqual(val_errors, [], f"Live evidence validation failed: {val_errors}")
        certified, reason = is_stage3_certified(evidence, mode="live")
        self.assertTrue(certified, f"Live evidence failed certification: {reason}")

        # Atomic write of evidence JSON
        temp_evidence = self.evidence_path.with_suffix(f".tmp.{os.getpid()}")
        temp_evidence.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        temp_evidence.replace(self.evidence_path)


if __name__ == "__main__":
    unittest.main()
