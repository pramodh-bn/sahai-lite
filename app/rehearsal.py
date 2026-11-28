"""Stage 2 rehearsal engine: deterministic Alex/Dana negotiation rehearsal.

Offline mode only. The counterpart is a deterministic stand-in: no network,
no model, no paid calls. Sessions live in process memory.

Stage 4A extends each session with up to two compiled synthetic personas and
server-authoritative turns (see ``core.py``); the Stage 1-3 endpoints keep
their original shape and behaviour for bodyless sessions.

Hidden need (composite): a budget constraint and sign-on flexibility. It is
revealed only when a user utterance probes either side, and stays revealed
for the rest of that attempt. Retry starts a fresh attempt at the practice
pivot; earlier attempts are kept unchanged.
"""
import copy
import uuid

from flask import Blueprint, jsonify, request

import persona
import state

MODE = state.MODE
SCENARIO = state.SCENARIO
VALID_TRANSITIONS = {("demo", "take_my_seat"), ("take_my_seat", "practice")}
BUDGET_TRIGGERS = ("budget", "cost", "price", "afford")
SIGN_ON_TRIGGERS = ("sign-on", "sign on", "signing bonus", "flexible on sign-on", "contract", "terms")

bp = Blueprint("rehearsal", __name__, url_prefix="/api/rehearsal")

# Backwards-compatible accessor used by the Stage 3 Napster adapter.
_get_session = state.get_session


def _is_probe(utterance):
    text = utterance.lower()
    return any(k in text for k in BUDGET_TRIGGERS) or any(k in text for k in SIGN_ON_TRIGGERS)


def _counterpart_reply(attempt, probe, was_revealed):
    turns = len(attempt["user_turns"])
    if probe and not was_revealed:
        return ("Honestly, budget is my hard constraint, and I'm flexible on sign-on "
                "if the number works for both of us.")
    if attempt["hidden_need_revealed"]:
        return (f"We've already covered the budget and sign-on point (turn {turns}). "
                "What structure would work for you?")
    return "Thanks. What would you need to see to move this forward?"


def _not_found():
    return jsonify({"error": "not_found"}), 404


def _requested_personas(body):
    """Return (personas, error_response). ``personas`` maps role -> entry."""
    requested = body.get("personas") if isinstance(body, dict) else None
    if requested is None:
        return {}, None
    if not isinstance(requested, dict):
        return None, (jsonify({"error": "persona_unavailable"}), 400)
    bound = {}
    for role in ("body_double", "counterpart"):
        ref = requested.get(role)
        entry = persona.get_persona(ref) if isinstance(ref, str) else None
        if entry is None:
            return None, (jsonify({"error": "persona_unavailable"}), 400)
        if entry["profile"].get("role") != role:
            return None, (jsonify({"error": "persona_role_mismatch"}), 400)
        bound[role] = entry
    return bound, None


@bp.route("/sessions", methods=["POST"])
def create_session():
    body = request.get_json(silent=True)
    if body is None:
        body = {}
    if not isinstance(body, dict):
        body = {}
    personas, error = _requested_personas(body)
    if error is not None:
        return error
    session = state.create_session(personas)
    response = {
        "session_id": session["session_id"],
        "state": "demo",
        "scenario": SCENARIO,
        "mode": MODE,
        "attempt": 1,
    }
    if personas:
        response.update({
            "profile_hashes": state.profile_hashes(session),
            "instruction_hashes": state.instruction_hashes(session),
            "authority_tier": persona.AUTHORITY_TIER,
            "policy_version": state.POLICY_VERSION,
            "next_seq": 1,
        })
    return jsonify(response), 201


@bp.route("/sessions/<session_id>/advance", methods=["POST"])
def advance(session_id):
    session = state.get_session(session_id)
    if session is None:
        return _not_found()
    body = request.get_json(silent=True) or {}
    target = body.get("to")
    with session["lock"]:
        if not isinstance(target, str) or (session["state"], target) not in VALID_TRANSITIONS:
            return jsonify({"error": "invalid_transition", "from": session["state"], "to": target}), 409
        session["state"] = target
        session["current"]["state"] = target
    return jsonify({"state": target}), 200


@bp.route("/sessions/<session_id>/practice", methods=["POST"])
def practice(session_id):
    session = state.get_session(session_id)
    if session is None:
        return _not_found()
    body = request.get_json(silent=True) or {}
    utterance = body.get("utterance")
    with session["lock"]:
        if session["state"] != "practice":
            return jsonify({"error": "invalid_state", "state": session["state"]}), 409
        if not isinstance(utterance, str) or not utterance.strip():
            return jsonify({"error": "invalid_utterance"}), 400
        utterance = utterance.strip()
        attempt = session["current"]
        was_revealed = attempt["hidden_need_revealed"]
        probe = _is_probe(utterance)
        if probe and not was_revealed:
            attempt["hidden_need_revealed"] = True
            attempt["revealed_at_seq"] = len(attempt["user_turns"]) + 1
        attempt["user_turns"].append({"utterance": utterance, "probe": probe})
        reply = _counterpart_reply(attempt, probe, was_revealed)
        attempt["transcript"].append({"speaker": "user", "utterance": utterance})
        attempt["transcript"].append({"speaker": "counterpart", "utterance": reply})
        attempt["next_seq"] = len([
            turn for turn in attempt["transcript"] if turn["speaker"] == "user"
        ]) + 1
        return jsonify({
            "counterpart_reply": reply,
            "hidden_need_revealed": attempt["hidden_need_revealed"],
        }), 200


@bp.route("/sessions/<session_id>/webcam-token", methods=["POST"])
def webcam_token(session_id):
    """Record a browser camera/microphone decision.

    Denial is a normal outcome: text practice stays available either way. A
    token is only minted when the camera is granted; it is a local, synthetic
    placeholder and is never a vendor credential.
    """
    session = state.get_session(session_id)
    if session is None:
        return _not_found()
    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        body = {}
    camera = body.get("camera", "denied")
    microphone = body.get("microphone", "denied")
    if camera not in ("granted", "denied") or microphone not in ("granted", "denied"):
        return jsonify({"error": "invalid_permission"}), 400
    with session["lock"]:
        attempt = session["current"]
        attempt["webcam"] = {
            "camera": camera,
            "microphone": microphone,
            "text_practice_available": True,
        }
    response = {
        "camera": camera,
        "microphone": microphone,
        "text_practice_available": True,
    }
    if camera == "granted":
        response["token"] = "webcam_" + uuid.uuid4().hex
    return jsonify(response), 200


@bp.route("/sessions/<session_id>/feedback", methods=["POST"])
def feedback(session_id):
    session = state.get_session(session_id)
    if session is None:
        return _not_found()
    with session["lock"]:
        if session["state"] not in ("practice", "feedback"):
            return jsonify({"error": "invalid_state", "state": session["state"]}), 409
        attempt = session["current"]
        if attempt["evidence_score"] is None:
            turns = attempt["user_turns"]
            probes = sum(1 for turn in turns if turn["probe"])
            attempt["evidence"] = [
                {
                    "utterance": turn["utterance"],
                    "note": ("probed the hidden need (budget and/or sign-on)" if turn["probe"]
                             else "exploratory turn, no probe of the hidden need"),
                }
                for turn in turns
            ]
            attempt["evidence_score"] = min(100, 15 * len(turns) + 30 * probes)
        if not attempt["feedback_recorded"]:
            for turn in attempt["user_turns"]:
                state.append_evidence(session, {
                    "record_type": "feedback_quote",
                    "attempt": attempt["attempt"],
                    "attempt_id": attempt["attempt_id"],
                    "quote": turn["utterance"],
                })
            attempt["feedback_recorded"] = True
        session["state"] = "feedback"
        attempt["state"] = "feedback"
        return jsonify({
            "state": "feedback",
            "attempt": attempt["attempt"],
            "evidence_score": attempt["evidence_score"],
            "evidence": copy.deepcopy(attempt["evidence"]),
        }), 200


@bp.route("/sessions/<session_id>/retry", methods=["POST"])
def retry(session_id):
    session = state.get_session(session_id)
    if session is None:
        return _not_found()
    with session["lock"]:
        if session["state"] != "feedback":
            return jsonify({"error": "invalid_state", "state": session["state"]}), 409
        new_attempt = state.new_attempt(session["current"]["attempt"] + 1)
        new_attempt["state"] = "practice"
        session["attempts"].append(new_attempt)
        session["current"] = new_attempt
        session["state"] = "practice"
        return jsonify({
            "state": "practice",
            "attempt": new_attempt["attempt"],
            "pivot_restored": True,
            "pivot": copy.deepcopy(session["pivot"]),
        }), 200


@bp.route("/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    session = state.get_session(session_id)
    if session is None:
        return _not_found()
    with session["lock"]:
        return jsonify(state.snapshot(session)), 200


@bp.route("/sessions/<session_id>/attempts", methods=["GET"])
def list_attempts(session_id):
    session = state.get_session(session_id)
    if session is None:
        return _not_found()
    with session["lock"]:
        return jsonify(state.attempts_view(session)), 200
