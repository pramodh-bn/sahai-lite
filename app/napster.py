"""Stage 3 server-side Napster adapter (WebRTC companion session).

Server-only: NAPSTER_API_KEY never leaves this process. Config is read from the
environment at request time:
  NAPSTER_BASE_URL  default https://companion-api.napster.com
  NAPSTER_API_KEY   required for a live allocation (X-Api-Key header)
  NAPSTER_AGENT_ID  required; scopes the connection to one agent

Without key and agent id the adapter reports OFFLINE and makes no upstream call.
Routes (under /api/rehearsal):
  POST   /sessions/<id>/napster-session  allocate one WebRTC connection
  DELETE /sessions/<id>/napster-session  tear it down

Rules: at most one upstream attempt plus one retry, and only for 409/429;
concurrent requests for the same session get 409 while one is in flight; a
failed attempt starts a cooldown; a post-allocation failure issues an upstream
DELETE immediately so nothing is left allocated.
"""
import http.client
import json
import math
import os
import threading
import time
import urllib.parse

from flask import Blueprint, jsonify, request

from rehearsal import _get_session

DEFAULT_BASE_URL = "https://companion-api.napster.com"
USER_AGENT = "sahai-lite/1.0"
UPSTREAM_TIMEOUT_S = 10
RETRY_DELAY_S = 0.5
COOLDOWN_S = 10.0
ALLOWED_SIMULATED_ERRORS = ("post_allocation_failure",)

bp = Blueprint("napster", __name__, url_prefix="/api/rehearsal")
_state_lock = threading.Lock()
# session_id -> {"connecting": bool, "cooldown_until": float, "connection": dict|None}
_state = {}


def _config():
    base = request_base_url()
    key = _env("NAPSTER_API_KEY")
    agent = _env("NAPSTER_AGENT_ID")
    return base, key, agent


def _env(name):
    return os.environ.get(name, "").strip()


def request_base_url():
    base = _env("NAPSTER_BASE_URL") or DEFAULT_BASE_URL
    return base.rstrip("/")


def _base_is_acceptable(base):
    parts = urllib.parse.urlsplit(base)
    if parts.scheme == "https" and parts.hostname:
        return True
    return parts.scheme == "http" and parts.hostname in ("127.0.0.1", "localhost")


def _send(method, url, headers, body=None):
    """Return (status, parsed_json_or_None). Header names are sent verbatim."""
    parts = urllib.parse.urlsplit(url)
    conn_cls = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"
    conn = conn_cls(parts.hostname, parts.port, timeout=UPSTREAM_TIMEOUT_S)
    try:
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        raw = resp.read()
        status = resp.status
    except (OSError, http.client.HTTPException):
        return 0, None
    finally:
        conn.close()
    try:
        data = json.loads(raw.decode("utf-8")) if raw else None
    except ValueError:
        data = None
    return status, data


def _auth_headers(key):
    return {"X-Api-Key": key, "User-Agent": USER_AGENT}


def _upstream_create(base, key, agent, external_id):
    headers = dict(_auth_headers(key))
    headers["Content-Type"] = "application/json"
    body = json.dumps({"channelType": "webrtc", "externalClientId": external_id}).encode("utf-8")
    return _send("POST", f"{base}/public/agents/{agent}/connections", headers, body)


def _upstream_delete(base, key, agent, connection_id):
    """True when the vendor no longer holds the connection (deleted or already gone)."""
    status, _ = _send(
        "DELETE",
        f"{base}/public/agents/{agent}/connections/{connection_id}",
        _auth_headers(key),
    )
    return status in (200, 202, 204, 404)


def _entry(session_id):
    return _state.setdefault(session_id, {"connecting": False, "cooldown_until": 0.0, "connection": None})


def _fail_with_cooldown(session_id, entry):
    entry["cooldown_until"] = time.monotonic() + COOLDOWN_S


@bp.route("/sessions/<session_id>/napster-session", methods=["POST"])
def create_napster_session(session_id):
    if _get_session(session_id) is None:
        return jsonify({"error": "not_found"}), 404
    body = request.get_json(silent=True) or {}
    channel_type = body.get("channel_type", "webrtc")
    if channel_type != "webrtc":
        return jsonify({"error": "unsupported_channel_type"}), 400
    simulate = body.get("simulate_error")
    if simulate not in (None, "") and simulate not in ALLOWED_SIMULATED_ERRORS:
        return jsonify({"error": "unsupported_simulate_error"}), 400

    base, key, agent = _config()
    if not key or not agent or not _base_is_acceptable(base):
        return jsonify({"status": "offline", "error": "napster_not_configured"}), 503

    now = time.monotonic()
    with _state_lock:
        entry = _entry(session_id)
        if entry["connecting"]:
            return jsonify({"status": "connecting", "error": "connection_in_flight"}), 409
        if entry["connection"] is not None:
            return jsonify({"status": "connected", "error": "already_connected"}), 409
        if now < entry["cooldown_until"]:
            retry_after = math.ceil(entry["cooldown_until"] - now)
            return jsonify({"status": "offline", "error": "cooldown", "retry_after_seconds": retry_after}), 429
        entry["connecting"] = True

    try:
        external_id = "sahai_" + session_id[:12]
        status, data = _upstream_create(base, key, agent, external_id)
        attempts = 1
        if status in (409, 429):
            time.sleep(RETRY_DELAY_S)
            status, data = _upstream_create(base, key, agent, external_id)
            attempts = 2

        token = data.get("token") if isinstance(data, dict) else None
        connection = data.get("connection") if isinstance(data, dict) else None
        connection_id = connection.get("id") if isinstance(connection, dict) else None
        allocated = status in (200, 201) and bool(token) and bool(connection_id)

        if not allocated:
            with _state_lock:
                _fail_with_cooldown(session_id, _entry(session_id))
            if status == 429:
                return jsonify({"status": "offline", "error": "vendor_rate_limited", "attempts": attempts}), 429
            return jsonify({"status": "offline", "error": "vendor_unavailable", "attempts": attempts}), 502

        if simulate == "post_allocation_failure":
            rolled_back = _upstream_delete(base, key, agent, connection_id)
            with _state_lock:
                _fail_with_cooldown(session_id, _entry(session_id))
            return jsonify({
                "status": "offline",
                "error": "post_allocation_failure",
                "rolled_back": rolled_back,
            }), 502

        with _state_lock:
            _entry(session_id)["connection"] = {
                "connection_id": connection_id,
                "base_url": base,
                "agent_id": agent,
            }
        return jsonify({"token": token, "connection_id": connection_id, "status": "ready"}), 200
    finally:
        with _state_lock:
            _entry(session_id)["connecting"] = False


@bp.route("/sessions/<session_id>/napster-session", methods=["DELETE"])
def delete_napster_session(session_id):
    if _get_session(session_id) is None:
        return jsonify({"error": "not_found"}), 404
    with _state_lock:
        entry = _state.get(session_id)
        connection = entry.get("connection") if entry else None
        if entry is not None:
            entry["connection"] = None
    if connection is None:
        return jsonify({"status": "no_active_connection", "session_destroyed": False}), 200

    key = _env("NAPSTER_API_KEY")
    destroyed = bool(key) and _upstream_delete(
        connection["base_url"], key, connection["agent_id"], connection["connection_id"]
    )
    if not destroyed:
        return jsonify({"status": "vendor_delete_failed", "session_destroyed": False}), 502
    return jsonify({"status": "destroyed", "session_destroyed": True}), 200
