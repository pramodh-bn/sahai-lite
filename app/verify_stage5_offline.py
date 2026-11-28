"""Offline self-check for Stage 5 (two avatars, webcam, coach, summary).

Runs the Flask app in-process with no credentials and no network: upstream
sends are replaced by local stubs that record the request. This is builder
evidence, not the independent acceptance contract.

Run with: py -3.12 app/verify_stage5_offline.py
"""
import json
import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import coach  # noqa: E402
import main as app_main  # noqa: E402
import napster  # noqa: E402

ENV_KEYS = (
    "NAPSTER_BASE_URL",
    "NAPSTER_API_KEY",
    "NAPSTER_AGENT_ID",
    "NAPSTER_ALEX_AGENT_ID",
    "FIREWORKS_API_KEY",
    "FIREWORKS_BASE_URL",
)


def _clear_env():
    for name in ENV_KEYS:
        os.environ.pop(name, None)


def _new_session(client):
    resp = client.post("/api/rehearsal/sessions", json={})
    assert resp.status_code == 201, (resp.status_code, resp.get_json())
    return resp.get_json()["session_id"]


def _to_practice(client, sid):
    assert client.post(
        "/api/rehearsal/sessions/%s/advance" % sid, json={"to": "take_my_seat"}
    ).status_code == 200
    assert client.post(
        "/api/rehearsal/sessions/%s/advance" % sid, json={"to": "practice"}
    ).status_code == 200


def proof_webcam_token():
    client = app_main.app.test_client()
    sid = _new_session(client)
    ok = client.post(
        "/api/rehearsal/sessions/%s/webcam-token" % sid,
        json={"camera": "granted", "microphone": "granted"},
    )
    body = ok.get_json()
    assert ok.status_code == 200, body
    assert body["camera"] == "granted" and body.get("token"), body
    assert body["text_practice_available"] is True

    denied = client.post(
        "/api/rehearsal/sessions/%s/webcam-token" % sid,
        json={"camera": "denied", "microphone": "denied"},
    ).get_json()
    assert denied["camera"] == "denied" and denied["text_practice_available"] is True
    assert "token" not in denied

    missing = client.post(
        "/api/rehearsal/sessions/does-not-exist/webcam-token", json={"camera": "granted"}
    )
    assert missing.status_code == 404
    print("WEBCAM_PROOF_OK granted_token=%s denial_text_ok=1 unknown=404"
          % bool(body.get("token")))


def proof_two_avatars():
    _clear_env()
    os.environ["NAPSTER_BASE_URL"] = "http://127.0.0.1:9"
    os.environ["NAPSTER_API_KEY"] = "offline-proof-key"
    os.environ["NAPSTER_AGENT_ID"] = "proof-dana-agent"
    os.environ["NAPSTER_ALEX_AGENT_ID"] = "proof-alex-agent"
    seen = []

    def fake_send(method, url, headers, body=None):
        if method == "POST":
            seen.append(url)
            agent = url.split("/public/agents/")[1].split("/")[0]
            n = len(seen)
            return 200, {
                "token": "proof-token-%d" % n,
                "connection": {"id": "proof-conn-%d" % n},
            }
        return 204, None

    original = napster._send
    napster._send = fake_send
    napster._state.clear()
    try:
        client = app_main.app.test_client()
        sid = _new_session(client)
        dana = client.post(
            "/api/rehearsal/sessions/%s/napster-session" % sid,
            json={"channel_type": "webrtc", "avatar": "dana"},
        )
        alex = client.post(
            "/api/rehearsal/sessions/%s/napster-session" % sid,
            json={"channel_type": "webrtc", "avatar": "alex"},
        )
        assert dana.status_code == 200, dana.get_json()
        assert alex.status_code == 200, alex.get_json()
        assert dana.get_json()["connection_id"] != alex.get_json()["connection_id"]
        duplicate = client.post(
            "/api/rehearsal/sessions/%s/napster-session" % sid, json={"avatar": "dana"}
        )
        assert duplicate.status_code == 409, duplicate.get_json()
        assert "proof-dana-agent" in seen[0] and "proof-alex-agent" in seen[1], seen
        receipt = client.delete("/api/rehearsal/sessions/%s" % sid).get_json()
        assert receipt["vendor_session_destroyed"] is True, receipt
        print("TWO_AVATAR_PROOF_OK events=%s duplicate=409 cleanup=%s"
              % (len(seen), receipt["vendor_session_destroyed"]))
    finally:
        napster._send = original
        napster._state.clear()
        _clear_env()


def proof_coach():
    _clear_env()
    os.environ["FIREWORKS_API_KEY"] = "offline-proof-fireworks-key"
    os.environ["FIREWORKS_BASE_URL"] = "http://127.0.0.1:9"
    calls = []

    def fake_send(url, headers, body):
        calls.append({"url": url, "headers": headers, "body": body.decode("utf-8")})
        return 200, {
            "choices": [{"message": {"role": "assistant", "content": "Probe sign-on."}}]
        }

    original = coach._send
    coach._send = fake_send
    try:
        client = app_main.app.test_client()
        sid = _new_session(client)
        _to_practice(client, sid)
        client.post(
            "/api/rehearsal/sessions/%s/practice" % sid,
            json={"utterance": "What budget range works?"},
        )
        whisper = client.post(
            "/api/rehearsal/sessions/%s/coach-whisper" % sid,
            json={"utterance": "What budget range works?", "accepted": False},
        )
        assert whisper.status_code == 200, whisper.get_json()
        assert whisper.get_json()["suggestion"] and whisper.get_json()["context"]
        assert calls and calls[-1]["url"].endswith("/inference/v1/chat/completions")
        assert calls[-1]["headers"]["Authorization"] == "Bearer offline-proof-fireworks-key"
        assert "What budget range works?" in calls[-1]["body"]

        second = client.post(
            "/api/rehearsal/sessions/%s/coach-whisper" % sid,
            json={"utterance": "Would sign-on flexibility help?", "accepted": True},
        )
        assert second.status_code == 200, second.get_json()
        client.post("/api/rehearsal/sessions/%s/practice" % sid,
                    json={"utterance": "Would sign-on flexibility help?"})
        fb = client.post("/api/rehearsal/sessions/%s/feedback" % sid, json={})
        assert fb.status_code == 200, fb.get_json()
        summary = client.get("/api/rehearsal/sessions/%s/coach-summary" % sid)
        data = summary.get_json()
        assert summary.status_code == 200, data
        assert data["turns_shown"] == 2 and data["turns_accepted"] == 1, data
        assert isinstance(data["corrections"], list)

        no_key_sid = _new_session(client)
        _to_practice(client, no_key_sid)
        before = len(calls)
        _clear_env()
        unavailable = client.post(
            "/api/rehearsal/sessions/%s/coach-whisper" % no_key_sid,
            json={"utterance": "hi"},
        )
        assert unavailable.status_code == 503, unavailable.get_json()
        assert unavailable.get_json()["error"] == "coach_not_configured"
        assert len(calls) == before, "coach called upstream without a key"
        print("COACH_PROOF_OK upstream=%s summary=%s unconfigured=503"
              % (len(calls), (data["turns_shown"], data["turns_accepted"])))
    finally:
        coach._send = original
        _clear_env()


if __name__ == "__main__":
    proof_webcam_token()
    proof_two_avatars()
    proof_coach()
    print("STAGE5_OFFLINE_SELFCHECK_PASS")
