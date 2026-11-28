"""Stage 5 console coach: synchronous whisper suggestions and a summary.

Server-only. Configuration is read at request time:
  FIREWORKS_API_KEY   required; when absent the coach is honestly unavailable
  FIREWORKS_BASE_URL  optional origin override (default api.fireworks.ai);
                      a loopback http origin is accepted for test fakes

Routes (under /api/rehearsal):
  POST /sessions/<id>/coach-whisper  one synchronous suggestion
  GET  /sessions/<id>/coach-summary  counts for the current attempt

No key -> typed 503 ``coach_not_configured`` and no upstream call. The key is
never returned to the browser and never logged.
"""
import copy
import http.client
import json
import os
import urllib.parse

from flask import Blueprint, jsonify, request

import state

DEFAULT_BASE_URL = "https://api.fireworks.ai"
CHAT_COMPLETIONS_PATH = "/inference/v1/chat/completions"
UPSTREAM_TIMEOUT_S = 15
COACH_SYSTEM_PROMPT = (
    "You are a discreet negotiation coach whispering to a job candidate during "
    "a live practice call. Suggest one concrete thing they can say or ask next. "
    "Be brief and specific."
)

bp = Blueprint("coach", __name__, url_prefix="/api/rehearsal")


def _env(name):
    return os.environ.get(name, "").strip()


def _base_url():
    return (_env("FIREWORKS_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def _base_is_acceptable(base):
    parts = urllib.parse.urlsplit(base)
    if parts.scheme == "https" and parts.hostname:
        return True
    return parts.scheme == "http" and parts.hostname in ("127.0.0.1", "localhost")


def _send(url, headers, body):
    """POST JSON and return (status, parsed_json_or_None)."""
    parts = urllib.parse.urlsplit(url)
    conn_cls = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    path = parts.path or "/"
    if parts.query:
        path = "%s?%s" % (path, parts.query)
    conn = conn_cls(parts.hostname, parts.port, timeout=UPSTREAM_TIMEOUT_S)
    try:
        conn.request("POST", path, body=body, headers=headers)
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


def _latest_turn(attempt):
    turns = attempt.get("user_turns") or []
    if not turns:
        return ""
    latest = turns[-1].get("utterance", "")
    return latest if isinstance(latest, str) else ""


def _context(attempt, turn_number):
    revealed = "revealed" if attempt.get("hidden_need_revealed") else "not yet revealed"
    return (
        "Attempt %s, practice turn %d; hidden need %s."
        % (attempt.get("attempt"), turn_number, revealed)
    )


def _suggestion_from(data):
    if not isinstance(data, dict):
        return ""
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    return content.strip() if isinstance(content, str) else ""


@bp.route("/sessions/<session_id>/coach-whisper", methods=["POST"])
def coach_whisper(session_id):
    session = state.get_session(session_id)
    if session is None:
        return jsonify({"error": "not_found"}), 404
    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        body = {}

    key = _env("FIREWORKS_API_KEY")
    if not key:
        return jsonify({
            "status": "unavailable",
            "error": "coach_not_configured",
            "text_practice_available": True,
        }), 503
    base = _base_url()
    if not _base_is_acceptable(base):
        return jsonify({"status": "unavailable", "error": "coach_not_configured"}), 503

    with session["lock"]:
        attempt = session["current"]
        utterance = body.get("utterance")
        if not isinstance(utterance, str) or not utterance.strip():
            utterance = _latest_turn(attempt)
        else:
            utterance = utterance.strip()
        turn_number = len(attempt.get("user_turns") or []) or 1

    payload = {
        "model": "accounts/fireworks/models/llama-v3p1-8b-instruct",
        "messages": [
            {"role": "system", "content": COACH_SYSTEM_PROMPT},
            {"role": "user", "content": utterance},
        ],
        "max_tokens": 160,
        "temperature": 0.4,
    }
    headers = {
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        "User-Agent": "sahai-lite/1.0",
    }
    status, data = _send(
        base + CHAT_COMPLETIONS_PATH, headers,
        json.dumps(payload).encode("utf-8"),
    )
    suggestion = _suggestion_from(data)
    if status not in (200, 201) or not suggestion:
        return jsonify({"status": "unavailable", "error": "coach_unavailable"}), 502

    accepted = body.get("accepted") is True
    context = _context(attempt, turn_number)
    with session["lock"]:
        coach = attempt.setdefault("coach", {
            "turns_shown": 0, "turns_accepted": 0, "corrections": [],
        })
        coach["turns_shown"] += 1
        coach["turns_accepted"] += 1 if accepted else 0
        if not accepted:
            coach["corrections"].append({
                "turn": coach["turns_shown"],
                "note": suggestion,
            })
    return jsonify({"suggestion": suggestion, "context": context}), 200


@bp.route("/sessions/<session_id>/coach-summary", methods=["GET"])
def coach_summary(session_id):
    session = state.get_session(session_id)
    if session is None:
        return jsonify({"error": "not_found"}), 404
    with session["lock"]:
        attempt = session["current"]
        if session.get("state") not in ("feedback", "ended"):
            return jsonify({
                "error": "summary_not_available",
                "state": session.get("state"),
            }), 409
        coach = attempt.setdefault("coach", {
            "turns_shown": 0, "turns_accepted": 0, "corrections": [],
        })
        return jsonify({
            "turns_shown": coach["turns_shown"],
            "turns_accepted": coach["turns_accepted"],
            "corrections": copy.deepcopy(coach["corrections"]),
        }), 200
