"""Requirement 7: Separate immutable live-only module.

Mandate:
- Requires SAH_NAPSTER_LIVE=1, NAPSTER_API_KEY, and NAPSTER_AGENT_ID.
- Gate absent: skips explicitly as non-certifying with zero vendor calls (exit 0) and creates no files.
- Gate open:
    * Single browser-owned flow without direct test preallocation.
    * Fresh evidence target required (SAH_STAGE3_EVIDENCE_PATH must not exist before test; temp file cleaned on write failure).
    * Bounded duration: 30.0s monotonic deadline established at start; all waits, clicks, and checks use remaining milliseconds.
    * Reserved cleanup time (5.0s); halts waiting and triggers bounded cleanup immediately on deadline exhaustion.
    * Request observer counts outgoing connection POST and DELETE; cleanup_attempted['sent'] set only when outgoing DELETE request is observed.
    * Explicit remaining-deadline timeout passed to connect_btn.click() and disconnect_btn.click().
    * Exact observed POST status 200 required without fallback substitution.
    * Host Policy: Credentialed certification strictly requires HTTPS and exact approved real host companion-api.napster.com; rejects loopback, private IPs, aliases, and historical hosts.
    * Connection ID hashed immediately with SHA-256 for lowercase correlation hash; vendor path redacted as /public/agents/[REDACTED]/connections.
    * Deadline-bound page.wait_for_function awaits complete readiness predicate before evaluation (readyVideo, onAvatarReady(true), mounted live video, audio-owned live track).
    * Deterministic disconnect observation with expect_response.
    * Deadline-bound page.wait_for_function awaits complete release predicate before evaluation (no live tracks, cleared media, avatarReady false, sdkStatus unavailable).
    * Fallback cleanup in finally runs only when no DELETE request was observed, passing remaining cleanup timeout to delete_napster_session().
    * Indeterminate cleanup guard: if connection request was observed without a session ID for fallback, fails prominently.
    * Non-success or indeterminate cleanup fails certification prominently, reporting possible retained upstream resources (zero test retries).
    * Validates evidence with validate_stage3_evidence(evidence, mode='live') and is_stage3_certified(evidence, mode='live').
    * Evidence records non-sensitive telemetry: active_duration_seconds, connection_create_requests=1, cleanup_requests=1.
    * Atomically writes validated redacted JSON to SAH_STAGE3_EVIDENCE_PATH.
- A mere HTTP 200 / token response CANNOT certify Stage 3.
"""
import hashlib
import json
import os
import sys
import time
import unittest
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from s2_helpers import AppProcess, app_base_url
from s3_helpers import delete_napster_session, is_stage3_certified, validate_stage3_evidence

OFFICIAL_CERTIFIED_HOST = "companion-api.napster.com"
LIVE_TOTAL_BUDGET_S = 30.0
CLEANUP_RESERVE_S = 5.0


def derive_and_validate_live_vendor_host():
    raw_base = os.environ.get("NAPSTER_BASE_URL", "").strip()
    if raw_base:
        parsed = urllib.parse.urlsplit(raw_base if "//" in raw_base else f"https://{raw_base}")
        if parsed.scheme and parsed.scheme.lower() != "https":
            raise RuntimeError(f"Live certification requires HTTPS base URL; got scheme '{parsed.scheme}'")
        if parsed.username or parsed.password:
            raise RuntimeError("Userinfo is strictly forbidden in NAPSTER_BASE_URL")
        if parsed.port and parsed.port != 443:
            raise RuntimeError(f"Non-default port '{parsed.port}' is forbidden in NAPSTER_BASE_URL")
        host = (parsed.hostname or "").lower()
    else:
        host = OFFICIAL_CERTIFIED_HOST

    if host != OFFICIAL_CERTIFIED_HOST:
        raise RuntimeError(
            f"Live certification requires exact approved real host '{OFFICIAL_CERTIFIED_HOST}'; "
            f"got '{host}'. Loopback, private IPs, aliases, and historical hosts are non-certifying."
        )
    return host



def observe_live_response(
    url: str,
    method: str,
    status: int,
    data: object,
    session_id_holder: dict,
    conn_hash_holder: dict,
    cleanup_holder: dict | None = None,
) -> None:
    """
    Pure response-observation function used directly by the Playwright on_response callback.
    Classifies the specific /napster-session POST before generic rehearsal-session POST.
    Never retains or persists raw tokens or raw connection IDs.
    """
    method_upper = (method or "").upper()
    url_str = url or ""

    # 1. SPECIFIC FIRST: /napster-session POST (connection creation)
    if method_upper == "POST" and "/napster-session" in url_str:
        conn_hash_holder["post_status"] = status
        if status == 200 and isinstance(data, dict):
            conn_id = data.get("connection_id")
            if isinstance(conn_id, str) and conn_id.strip():
                # Immediately hash connection_id with SHA-256; never retain raw connection_id
                conn_hash_holder["hash"] = hashlib.sha256(conn_id.encode("utf-8")).hexdigest().lower()
            else:
                conn_hash_holder["hash"] = None
        else:
            conn_hash_holder["hash"] = None
        return

    # 2. SPECIFIC: /napster-session DELETE (teardown/cleanup)
    if method_upper == "DELETE" and "/napster-session" in url_str:
        if cleanup_holder is not None:
            cleanup_holder["status_code"] = status
            if isinstance(data, dict):
                cleanup_holder["destroyed"] = (
                    data.get("status") == "destroyed"
                    and data.get("session_destroyed") is True
                )
                cleanup_holder["error"] = data.get("error")
                if data.get("status") == "no_active_connection":
                    cleanup_holder["no_active_connection"] = True
            else:
                cleanup_holder["error"] = "non-dict or malformed delete response"
        return

    # 3. GENERIC: rehearsal session creation POST (mutually exclusive with /napster-session, /advance, etc.)
    if method_upper == "POST" and "/api/rehearsal/sessions" in url_str:
        if not (
            "/napster-session" in url_str
            or "/advance" in url_str
            or "/practice" in url_str
            or "/feedback" in url_str
            or "/retry" in url_str
        ):
            if isinstance(data, dict) and "session_id" in data:
                session_id_holder["session_id"] = data["session_id"]
        return


def build_stage3_live_evidence(
    *,
    start_time_utc: str,
    end_time_utc: str,
    elapsed_seconds: float,
    post_connection_count: int,
    delete_connection_count: int,
    probe_correlation_hash: str | None,
    post_status: int | None,
    configured_host: str,
) -> dict:
    return {
        "start_time_utc": start_time_utc,
        "end_time_utc": end_time_utc,
        "active_duration_seconds": round(elapsed_seconds, 3),
        "connection_create_requests": post_connection_count,
        "cleanup_requests": delete_connection_count,
        "probe_correlation_hash": probe_correlation_hash,
        "http_probe": {
            "host": configured_host,
            "scheme": "https",
            "path": "/public/agents/[REDACTED]/connections",
            "method": "POST",
            "status_code": post_status,
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


def write_atomic_stage3_evidence(evidence: dict, target_path: Path) -> Path:
    target_path = Path(target_path)
    temp_evidence = target_path.with_suffix(f".tmp.{os.getpid()}")
    try:
        temp_evidence.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        temp_evidence.replace(target_path)
    except Exception:
        if temp_evidence.exists():
            try:
                temp_evidence.unlink()
            except Exception:
                pass
        raise
    return target_path


def build_validate_and_write_stage3_evidence(
    *,
    start_time_utc: str,
    end_time_utc: str,
    elapsed_seconds: float,
    post_connection_count: int,
    delete_connection_count: int,
    probe_correlation_hash: str | None,
    post_status: int | None,
    configured_host: str,
    target_path: Path,
    mode: str = "live",
) -> dict:
    evidence = build_stage3_live_evidence(
        start_time_utc=start_time_utc,
        end_time_utc=end_time_utc,
        elapsed_seconds=elapsed_seconds,
        post_connection_count=post_connection_count,
        delete_connection_count=delete_connection_count,
        probe_correlation_hash=probe_correlation_hash,
        post_status=post_status,
        configured_host=configured_host,
    )
    val_errors = validate_stage3_evidence(evidence, mode=mode)
    if val_errors:
        raise ValueError(f"Stage 3 evidence validation failed ({mode=}): {val_errors}")
    certified, reason = is_stage3_certified(evidence, mode=mode)
    if not certified:
        raise ValueError(f"Stage 3 evidence certification failed ({mode=}): {reason}")
    write_atomic_stage3_evidence(evidence, target_path)
    return evidence


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
        if evidence_path.exists():
            raise RuntimeError(
                f"SAH_STAGE3_EVIDENCE_PATH ({evidence_path}) already exists; fresh evidence target required"
            )

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

        derive_and_validate_live_vendor_host()

        cls.app = AppProcess().start()
        try:
            from playwright.sync_api import sync_playwright

            cls.playwright = sync_playwright().start()
            cls.browser = cls.playwright.chromium.launch(
                args=[
                    "--use-fake-ui-for-media-stream",
                    "--use-fake-device-for-media-stream",
                ]
            )
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
        deadline = t0 + LIVE_TOTAL_BUDGET_S
        start_time_utc = datetime.now(timezone.utc).isoformat()

        def get_remaining_timeout_ms(reserve_s=0.0):
            rem = (deadline - time.monotonic()) - reserve_s
            if rem <= 0.05:
                raise TimeoutError(
                    f"Monotonic budget exhausted (reserve={reserve_s}s, remaining={rem:.3f}s); "
                    f"halting wait immediately to execute bounded cleanup"
                )
            return max(1, int(rem * 1000))

        # Token / HTTP 200 alone cannot certify
        certified_token_only, _ = is_stage3_certified(
            {"token": "dummy", "ready_proof": None}, mode="live"
        )
        self.assertFalse(certified_token_only, "A mere HTTP 200/token must not certify")

        configured_host = derive_and_validate_live_vendor_host()

        session_id_holder = {"session_id": None}
        conn_hash_holder = {"hash": None, "post_status": None}
        cleanup_holder = {"destroyed": False, "status_code": None, "error": None}
        cleanup_attempted = {"sent": False}
        request_counts = {"post_connection": 0, "delete_connection": 0}

        context = self.browser.new_context()
        context.grant_permissions(["microphone"], origin=app_base_url())
        page = context.new_page()

        def on_request(request):
            url = request.url
            method = request.method
            if "/napster-session" in url and method == "POST":
                request_counts["post_connection"] += 1
            elif "/napster-session" in url and method == "DELETE":
                request_counts["delete_connection"] += 1
                cleanup_attempted["sent"] = True

        page.on("request", on_request)

        def on_response(response):
            url = response.url
            method = response.request.method
            status = response.status
            try:
                data = response.json()
            except Exception:
                data = None
            observe_live_response(
                url=url,
                method=method,
                status=status,
                data=data,
                session_id_holder=session_id_holder,
                conn_hash_holder=conn_hash_holder,
                cleanup_holder=cleanup_holder,
            )
        page.on("response", on_response)

        probe_exc = None
        try:
            page.goto(app_base_url() + "/", timeout=get_remaining_timeout_ms(reserve_s=CLEANUP_RESERVE_S))

            connect_btn = page.locator('[data-testid="napster-connect"]')
            connect_btn.wait_for(state="visible", timeout=get_remaining_timeout_ms(reserve_s=CLEANUP_RESERVE_S))
            connect_btn.click(timeout=get_remaining_timeout_ms(reserve_s=CLEANUP_RESERVE_S))

            avatar = page.locator('[data-testid="napster-avatar"]')
            avatar.wait_for(state="visible", timeout=get_remaining_timeout_ms(reserve_s=CLEANUP_RESERVE_S))

            video_el = avatar.locator("video")
            video_el.wait_for(state="visible", timeout=get_remaining_timeout_ms(reserve_s=CLEANUP_RESERVE_S))
            audio_el = avatar.locator("audio")
            audio_el.wait_for(state="attached", timeout=get_remaining_timeout_ms(reserve_s=CLEANUP_RESERVE_S))

            status_el = page.locator('[data-testid="napster-status"]')
            status_el.wait_for(state="visible", timeout=get_remaining_timeout_ms(reserve_s=CLEANUP_RESERVE_S))

            # Await the complete exact readiness predicate via page.wait_for_function
            page.wait_for_function('''() => {
                const avatar = document.querySelector('[data-testid="napster-avatar"]');
                const v = avatar ? avatar.querySelector("video") : null;
                const a = avatar ? avatar.querySelector("audio") : null;
                const vStream = v ? v.srcObject : null;
                const aStream = a ? a.srcObject : null;

                const vTracks = vStream ? vStream.getVideoTracks() : [];
                const aTracks = aStream ? aStream.getAudioTracks() : [];

                const hasLiveVideo = vTracks.length > 0 && vTracks.some(t => t.readyState === "live");
                const hasLiveAudioOnAudioElement = aTracks.length > 0 && aTracks.some(t => t.readyState === "live");

                const statusEl = document.querySelector('[data-testid="napster-status"]');
                const exactSdkStatus = window.__napsterSdkStatus !== undefined
                    ? window.__napsterSdkStatus
                    : (statusEl ? statusEl.getAttribute("data-sdk-status") : null);

                const exactAvatarReadyArg = window.__napsterAvatarReady !== undefined
                    ? window.__napsterAvatarReady
                    : (statusEl && statusEl.getAttribute("data-avatar-ready") === "true");

                return (
                    !!v &&
                    !!a &&
                    hasLiveVideo &&
                    hasLiveAudioOnAudioElement &&
                    exactSdkStatus === "readyVideo" &&
                    exactAvatarReadyArg === true
                );
            }''', timeout=get_remaining_timeout_ms(reserve_s=CLEANUP_RESERVE_S))

            media_eval = page.evaluate('''() => {
                const avatar = document.querySelector('[data-testid="napster-avatar"]');
                const v = avatar ? avatar.querySelector("video") : null;
                const a = avatar ? avatar.querySelector("audio") : null;
                const vStream = v ? v.srcObject : null;
                const aStream = a ? a.srcObject : null;

                const vTracks = vStream ? vStream.getVideoTracks() : [];
                const aTracks = aStream ? aStream.getAudioTracks() : [];

                const hasLiveVideo = vTracks.length > 0 && vTracks.some(t => t.readyState === "live");
                const hasLiveAudioOnAudioElement = aTracks.length > 0 && aTracks.some(t => t.readyState === "live");

                const statusEl = document.querySelector('[data-testid="napster-status"]');
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
                f"SDK status must be exact 'readyVideo', got {media_eval['exactSdkStatus']!r}",
            )
            self.assertIs(
                media_eval["exactAvatarReadyArg"],
                True,
                f"onAvatarReady callback payload must strictly be boolean True, got {media_eval['exactAvatarReadyArg']!r}",
            )

            disconnect_btn = page.locator('[data-testid="napster-disconnect"]')
            disconnect_btn.wait_for(state="visible", timeout=get_remaining_timeout_ms(reserve_s=CLEANUP_RESERVE_S))

            # Deterministic observation of DELETE response via expect_response
            cleanup_timeout_ms = get_remaining_timeout_ms(reserve_s=0.0)
            with page.expect_response(
                lambda r: "/napster-session" in r.url and r.request.method == "DELETE",
                timeout=cleanup_timeout_ms,
            ) as delete_info:
                disconnect_btn.click(timeout=cleanup_timeout_ms)

            delete_resp = delete_info.value
            cleanup_holder["status_code"] = delete_resp.status
            try:
                del_data = delete_resp.json()
                if isinstance(del_data, dict):
                    cleanup_holder["destroyed"] = (
                        del_data.get("status") == "destroyed"
                        and del_data.get("session_destroyed") is True
                    )
                    cleanup_holder["error"] = del_data.get("error")
            except Exception as parse_err:
                cleanup_holder["error"] = str(parse_err)

            self.assertEqual(
                cleanup_holder["status_code"],
                200,
                f"DELETE response status must be 200, got {cleanup_holder['status_code']}",
            )
            self.assertTrue(
                cleanup_holder["destroyed"],
                f"DELETE response was not session_destroyed: {cleanup_holder}",
            )

            # Await the complete release predicate via page.wait_for_function
            # Wait callback must return the exact boolean conjunction of all five release conditions
            page.wait_for_function('''() => {
                const avatar = document.querySelector('[data-testid="napster-avatar"]');
                const v = avatar ? avatar.querySelector("video") : null;
                const a = avatar ? avatar.querySelector("audio") : null;
                const vStream = v ? v.srcObject : null;
                const aStream = a ? a.srcObject : null;

                const vLive = vStream && vStream.getVideoTracks ? vStream.getVideoTracks().some(t => t.readyState === "live") : false;
                const aLive = aStream && aStream.getAudioTracks ? aStream.getAudioTracks().some(t => t.readyState === "live") : false;

                const avatarReady = window.__napsterAvatarReady;
                const sdkStatus = window.__napsterSdkStatus;

                const noLiveVideoTracks = !vLive;
                const noLiveAudioTracks = !aLive;
                const elementsCleared = (!v || v.srcObject === null) && (!a || a.srcObject === null);
                const avatarReadyFalse = avatarReady === false;
                const sdkStatusUnavailable = sdkStatus === "unavailable";

                return (
                    noLiveVideoTracks &&
                    noLiveAudioTracks &&
                    elementsCleared &&
                    avatarReadyFalse &&
                    sdkStatusUnavailable
                );
            }''', timeout=get_remaining_timeout_ms(reserve_s=0.0))

            release_eval = page.evaluate('''() => {
                const avatar = document.querySelector('[data-testid="napster-avatar"]');
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

        except BaseException as exc:
            probe_exc = exc
            raise
        finally:
            try:
                page.close()
            except Exception:
                pass
            try:
                context.close()
            except Exception:
                pass

            cleanup_safe = False
            cleanup_err_detail = None

            # Exactly-once cleanup guard:
            # If no DELETE request was observed at all:
            if not cleanup_attempted["sent"]:
                if session_id_holder["session_id"]:
                    rem_cleanup_s = deadline - time.monotonic()
                    if rem_cleanup_s <= 0.0:
                        cleanup_safe = False
                        cleanup_err_detail = (
                            f"Monotonic deadline exhausted before fallback cleanup could be issued "
                            f"(remaining={rem_cleanup_s:.3f}s <= 0); session {session_id_holder['session_id']} "
                            f"possibly retained upstream resource"
                        )
                    else:
                        cleanup_attempted["sent"] = True
                        request_counts["delete_connection"] += 1
                        status, res = delete_napster_session(
                            session_id_holder["session_id"], timeout=rem_cleanup_s
                        )
                        cleanup_holder["status_code"] = status
                        if status == 200 and res.get("session_destroyed") is True:
                            cleanup_safe = True
                            cleanup_holder["destroyed"] = True
                        elif status == 200 and res.get("status") == "no_active_connection":
                            if request_counts["post_connection"] == 0:
                                cleanup_safe = True
                                cleanup_holder["destroyed"] = True
                                cleanup_holder["no_active_connection"] = True
                            else:
                                cleanup_safe = False
                                cleanup_holder["destroyed"] = False
                                cleanup_err_detail = (
                                    "POST connection was observed over the network but fallback DELETE "
                                    "returned no_active_connection; inconsistent state with possible retained resource"
                                )
                                cleanup_holder["error"] = cleanup_err_detail
                        else:
                            cleanup_safe = False
                            cleanup_holder["destroyed"] = False
                            cleanup_holder["error"] = res
                elif request_counts["post_connection"] > 0:
                    # Connection request was observed but no session ID is available for fallback
                    cleanup_safe = False
                    cleanup_err_detail = (
                        "Connection request was observed but no session ID is available for fallback cleanup; "
                        "indeterminate state with possible retained resource"
                    )
                else:
                    # No connection POST observed and no session ID created
                    cleanup_safe = True
                    cleanup_holder["destroyed"] = True
            else:
                cleanup_safe = cleanup_holder.get("destroyed", False)
                if not cleanup_safe:
                    cleanup_err_detail = (
                        f"Observed DELETE returned non-success: status={cleanup_holder.get('status_code')}, "
                        f"detail={cleanup_holder.get('error')}"
                    )

            if cleanup_safe:
                # Cleanup is safe. If a probe exception occurred, let it re-raise without being masked
                if probe_exc is not None:
                    raise probe_exc
            else:
                cleanup_msg = (
                    f"Cleanup returned non-success or became indeterminate (possible retained upstream resource): "
                    f"status={cleanup_holder.get('status_code')}, detail={cleanup_err_detail or cleanup_holder.get('error')}"
                )
                if probe_exc is not None:
                    raise RuntimeError(
                        f"{cleanup_msg}; original probe failure was: {type(probe_exc).__name__}: {probe_exc}"
                    ) from probe_exc
                else:
                    raise RuntimeError(cleanup_msg)

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
        self.assertEqual(
            conn_hash_holder["post_status"],
            200,
            f"Expected observed POST status 200, got {conn_hash_holder['post_status']}",
        )

        end_time_utc = datetime.now(timezone.utc).isoformat()
        evidence = build_validate_and_write_stage3_evidence(
            start_time_utc=start_time_utc,
            end_time_utc=end_time_utc,
            elapsed_seconds=elapsed,
            post_connection_count=request_counts["post_connection"],
            delete_connection_count=request_counts["delete_connection"],
            probe_correlation_hash=conn_hash_holder["hash"],
            post_status=conn_hash_holder["post_status"],
            configured_host=configured_host,
            target_path=self.evidence_path,
            mode="live",
        )
        val_errors = validate_stage3_evidence(evidence, mode="live")
        self.assertEqual(val_errors, [], f"Live evidence validation failed: {val_errors}")
        certified, reason = is_stage3_certified(evidence, mode="live")
        self.assertTrue(certified, f"Live evidence failed certification: {reason}")


if __name__ == "__main__":
    unittest.main()
