"""Stage 2 rehearsal engine: deterministic Alex/Dana negotiation rehearsal.

Offline mode only. The counterpart is a deterministic stand-in: no network,
no model, no paid calls. Sessions live in process memory.

Hidden need (composite): a budget constraint and sign-on flexibility. It is
revealed only when a user utterance probes either side, and stays revealed
for the rest of that attempt. Retry starts a fresh attempt at the practice
pivot; earlier attempts are kept unchanged.
"""
import copy
import threading
import uuid

from flask import Blueprint, jsonify, request

MODE = "offline"
SCENARIO = "alex_dana"
VALID_TRANSITIONS = {("demo", "take_my_seat"), ("take_my_seat", "practice")}
BUDGET_TRIGGERS = ("budget", "cost", "price", "afford")
SIGN_ON_TRIGGERS = ("sign-on", "sign on", "signing bonus", "flexible on sign-on", "contract", "terms")

bp = Blueprint("rehearsal", __name__, url_prefix="/api/rehearsal")
_lock = threading.Lock()
_sessions = {}


def _is_probe(utterance):
    text = utterance.lower()
    return any(k in text for k in BUDGET_TRIGGERS) or any(k in text for k in SIGN_ON_TRIGGERS)


def _new_attempt(number):
    return {
        "attempt": number,
        "state": "demo",
        "hidden_need_revealed": False,
        "user_turns": [],
        "transcript": [],
        "evidence": [],
        "evidence_score": None,
    }


def _counterpart_reply(attempt, probe, was_revealed):
    turns = len(attempt["user_turns"])
    if probe and not was_revealed:
        return ("Honestly, budget is my hard constraint, and I'm flexible on sign-on "
                "if the number works for both of us.")
    if attempt["hidden_need_revealed"]:
        return (f"We've already covered the budget and sign-on point (turn {turns}). "
                "What structure would work for you?")
    return "Thanks. What would you need to see to move this forward?"


def _snapshot(session):
    attempt = session["current"]
    snap = {
        "session_id": session["session_id"],
        "state": session["state"],
        "attempt": attempt["attempt"],
        "mode": MODE,
        "scenario": SCENARIO,
        "hidden_need_revealed": attempt["hidden_need_revealed"],
        "transcript": copy.deepcopy(attempt["transcript"]),
    }
    if attempt["evidence_score"] is not None:
        snap["evidence_score"] = attempt["evidence_score"]
    return snap


def _get_session(session_id):
    with _lock:
        return _sessions.get(session_id)


def _not_found():
    return jsonify({"error": "not_found"}), 404


@bp.route("/sessions", methods=["POST"])
def create_session():
    session_id = uuid.uuid4().hex
    first = _new_attempt(1)
    session = {"session_id": session_id, "state": "demo", "attempts": [first], "current": first}
    with _lock:
        _sessions[session_id] = session
    return jsonify({
        "session_id": session_id,
        "state": "demo",
        "scenario": SCENARIO,
        "mode": MODE,
        "attempt": 1,
    }), 201


@bp.route("/sessions/<session_id>/advance", methods=["POST"])
def advance(session_id):
    session = _get_session(session_id)
    if session is None:
        return _not_found()
    body = request.get_json(silent=True) or {}
    target = body.get("to")
    with _lock:
        if not isinstance(target, str) or (session["state"], target) not in VALID_TRANSITIONS:
            return jsonify({"error": "invalid_transition", "from": session["state"], "to": target}), 409
        session["state"] = target
        session["current"]["state"] = target
    return jsonify({"state": target}), 200


@bp.route("/sessions/<session_id>/practice", methods=["POST"])
def practice(session_id):
    session = _get_session(session_id)
    if session is None:
        return _not_found()
    body = request.get_json(silent=True) or {}
    utterance = body.get("utterance")
    with _lock:
        if session["state"] != "practice":
            return jsonify({"error": "invalid_state", "state": session["state"]}), 409
        if not isinstance(utterance, str) or not utterance.strip():
            return jsonify({"error": "invalid_utterance"}), 400
        utterance = utterance.strip()
        attempt = session["current"]
        was_revealed = attempt["hidden_need_revealed"]
        probe = _is_probe(utterance)
        if probe:
            attempt["hidden_need_revealed"] = True
        attempt["user_turns"].append({"utterance": utterance, "probe": probe})
        reply = _counterpart_reply(attempt, probe, was_revealed)
        attempt["transcript"].append({"speaker": "user", "utterance": utterance})
        attempt["transcript"].append({"speaker": "counterpart", "utterance": reply})
        return jsonify({
            "counterpart_reply": reply,
            "hidden_need_revealed": attempt["hidden_need_revealed"],
        }), 200


@bp.route("/sessions/<session_id>/feedback", methods=["POST"])
def feedback(session_id):
    session = _get_session(session_id)
    if session is None:
        return _not_found()
    with _lock:
        if session["state"] != "practice":
            return jsonify({"error": "invalid_state", "state": session["state"]}), 409
        attempt = session["current"]
        turns = attempt["user_turns"]
        probes = sum(1 for t in turns if t["probe"])
        attempt["evidence"] = [
            {
                "utterance": t["utterance"],
                "note": ("probed the hidden need (budget and/or sign-on)" if t["probe"]
                         else "exploratory turn, no probe of the hidden need"),
            }
            for t in turns
        ]
        attempt["evidence_score"] = min(100, 15 * len(turns) + 30 * probes)
        session["state"] = "feedback"
        attempt["state"] = "feedback"
        return jsonify({
            "state": "feedback",
            "evidence_score": attempt["evidence_score"],
            "evidence": copy.deepcopy(attempt["evidence"]),
        }), 200


@bp.route("/sessions/<session_id>/retry", methods=["POST"])
def retry(session_id):
    session = _get_session(session_id)
    if session is None:
        return _not_found()
    with _lock:
        if session["state"] != "feedback":
            return jsonify({"error": "invalid_state", "state": session["state"]}), 409
        new_attempt = _new_attempt(session["current"]["attempt"] + 1)
        new_attempt["state"] = "practice"
        session["attempts"].append(new_attempt)
        session["current"] = new_attempt
        session["state"] = "practice"
        return jsonify({
            "state": "practice",
            "attempt": new_attempt["attempt"],
            "pivot_restored": True,
        }), 200


@bp.route("/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    session = _get_session(session_id)
    if session is None:
        return _not_found()
    with _lock:
        return jsonify(_snapshot(session)), 200


@bp.route("/sessions/<session_id>/attempts", methods=["GET"])
def list_attempts(session_id):
    session = _get_session(session_id)
    if session is None:
        return _not_found()
    with _lock:
        out = []
        for attempt in session["attempts"]:
            entry = {
                "attempt": attempt["attempt"],
                "state": attempt["state"],
                "hidden_need_revealed": attempt["hidden_need_revealed"],
                "transcript": copy.deepcopy(attempt["transcript"]),
            }
            if attempt["evidence_score"] is not None:
                entry["evidence_score"] = attempt["evidence_score"]
            out.append(entry)
        return jsonify({"attempts": out}), 200
