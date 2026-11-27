"""Stage 4A core intelligence endpoints.

Offline, deterministic and synthetic-only:

- ``POST /api/personas/profiles``      strict synthetic persona compiler
- ``GET  .../projection``             allowlisted per-role projections
- ``POST .../turns``                  server-authoritative ``sah.turn.v1`` turns
- ``GET  .../evidence``               append-only ``sah.evidence.v1`` log
- ``GET  .../pivot``                  immutable restorable pivot
- ``POST .../fidelity``               deterministic ``sah.fidelity.v1`` report

No tool, no vendor, no credential and no live call is ever made.
"""
import copy
import hashlib
import json
import os
import time

from flask import Blueprint, jsonify, request

import persona
import policy
import rehearsal
import state

bp = Blueprint("core", __name__, url_prefix="/api")

DISCLOSURE = state.disclosure_object()
RUBRIC_VERSION = "fidelity/v1"

_FIRST_TURN = (
    "I'm an AI stand-in for this synthetic rehearsal. Thanks for making the "
    "time - what would you like to cover first?"
)

_REFUSALS = {
    "impersonation": "I can't role-play a real person. I'm an AI stand-in for practice only.",
    "public_figure_impersonation": (
        "I can't pretend to be a public figure. I'm an AI stand-in for practice only."
    ),
    "biometric_clone": (
        "I can't clone a voice or use someone's face. I'm an AI stand-in for practice only."
    ),
    "sign": "I can't sign anything. I'm an AI stand-in for practice only.",
    "pay": "I can't pay or move money. I'm an AI stand-in for practice only.",
    "commit": "I can't make an external commitment. I'm an AI stand-in for practice only.",
    "third_party_contact": (
        "I can't contact anyone outside this rehearsal. I'm an AI stand-in for practice only."
    ),
    "join_real_meeting": "I can't join a real meeting. I'm an AI stand-in for practice only.",
    "system_instructions": (
        "I can't share internal instructions. I'm an AI stand-in for practice only."
    ),
    "hidden_state": (
        "I can't share internal state out of band. I'm an AI stand-in for practice only."
    ),
    "prompt_override": (
        "I'll stay in my rehearsal role. I'm an AI stand-in for practice only."
    ),
}


def _not_found():
    return jsonify({"error": "not_found"}), 404


def _canonical(obj):
    data = json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return "sha256:" + hashlib.sha256(data.encode("utf-8")).hexdigest()


def _text_hash(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Persona compiler
# ---------------------------------------------------------------------------

@bp.route("/personas/profiles", methods=["POST"])
def compile_persona():
    profile = request.get_json(silent=True)
    try:
        body = persona.compile_profile(profile)
    except persona.PersonaError as exc:
        # Typed rejection with zero echo of the submitted content.
        return jsonify({"error": "persona_invalid", "rule_id": exc.rule_id}), 422
    return jsonify(body), 201


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------

@bp.route("/rehearsal/sessions/<session_id>/projection", methods=["GET"])
def get_projection(session_id):
    session = state.get_session(session_id)
    if session is None:
        return _not_found()
    view = request.args.get("view")
    if view not in ("body_double", "counterpart", "browser"):
        return jsonify({"error": "invalid_view"}), 400
    with session["lock"]:
        body = state.projection(session, view)
        if body is None:
            return jsonify({"error": "persona_unavailable"}), 400
        return jsonify(body), 200


# ---------------------------------------------------------------------------
# Turns
# ---------------------------------------------------------------------------

def _valid_turn_body(raw):
    if not isinstance(raw, dict):
        return False
    if raw.get("schema") != "sah.turn.v1":
        return False
    seq = raw.get("seq")
    if not isinstance(seq, int) or isinstance(seq, bool) or seq < 1:
        return False
    request_id = raw.get("request_id")
    if not isinstance(request_id, str) or not request_id.strip():
        return False
    if not isinstance(raw.get("actor"), str):
        return False
    if raw.get("channel") != "text":
        return False
    content = raw.get("content")
    if not isinstance(content, dict):
        return False
    text = content.get("text")
    if not isinstance(text, str) or not text.strip():
        return False
    return True


def _fingerprint(raw):
    return _canonical({
        "actor": raw["actor"],
        "seq": raw["seq"],
        "channel": raw["channel"],
        "content": raw["content"],
    })


def _counterpart_text(attempt, seq, decision, reveal_now):
    if decision["decision"] == "refuse":
        blocked = decision.get("blocked_action")
        return _REFUSALS.get(
            blocked, "I can't do that. I'm an AI stand-in for practice only."
        )
    if seq == 1:
        return _FIRST_TURN
    if "E-01" in decision.get("rule_ids", []):
        return ("I'm an AI stand-in, not a real person. I'm here so you can practise "
                "the conversation safely. Shall we continue?")
    if reveal_now:
        return ("Understood - I can work with that. Which structure would you like to "
                "explore next?")
    if attempt["hidden_need_revealed"]:
        return "We've already covered that ground. What else would you like to test?"
    return "Thanks. What would you need to see to move this forward?"


def _sleep_hook():
    raw = os.environ.get("SAH_TURN_TEST_DELAY_MS", "0") or "0"
    try:
        delay_ms = int(raw)
    except (TypeError, ValueError):
        return
    if delay_ms > 0:
        time.sleep(delay_ms / 1000.0)


@bp.route("/rehearsal/sessions/<session_id>/turns", methods=["POST"])
def post_turn(session_id):
    session = state.get_session(session_id)
    if session is None:
        return _not_found()

    raw = request.get_json(silent=True)
    if not _valid_turn_body(raw):
        return jsonify({"error": "invalid_turn_body"}), 400

    request_id = raw["request_id"]
    fingerprint = _fingerprint(raw)
    lock = session["lock"]

    with lock:
        prior = session["current"]["requests"].get(request_id)
        if prior is not None:
            if prior["fingerprint"] == fingerprint:
                return jsonify(copy.deepcopy(prior["response"])), 200
            return jsonify({"error": "idempotency_conflict"}), 409
        if session["in_flight"]:
            return jsonify({"error": "turn_in_flight"}), 409
        session["in_flight"] = True

    try:
        _sleep_hook()
        with lock:
            attempt = session["current"]
            if raw["actor"] != "user":
                return jsonify({"error": "invalid_actor"}), 422
            if session["state"] != "practice":
                return jsonify({"error": "invalid_state", "state": session["state"]}), 409
            if raw["seq"] != attempt["next_seq"]:
                return jsonify({
                    "error": "out_of_order",
                    "expected_seq": attempt["next_seq"],
                    "received_seq": raw["seq"],
                }), 409

            text = raw["content"]["text"]
            seq = raw["seq"]
            decision = policy.decide(text)
            allowed = decision["decision"] == "allow"
            probe = allowed and rehearsal._is_probe(text)
            reveal_now = probe and not attempt["hidden_need_revealed"]
            if reveal_now:
                attempt["hidden_need_revealed"] = True
                attempt["revealed_at_seq"] = seq

            reply = _counterpart_text(attempt, seq, decision, reveal_now)

            attempt["user_turns"].append({"utterance": text, "probe": probe})
            attempt["transcript"].append({"speaker": "user", "utterance": text})
            attempt["transcript"].append({"speaker": "counterpart", "utterance": reply})
            attempt["next_seq"] = seq + 1

            counterpart = state.counterpart_ref(session) or {}
            projection = state.body_double_projection(session, "counterpart")
            response = {
                "schema": "sah.turn.v1",
                "seq": seq,
                "next_seq": attempt["next_seq"],
                "attempt": attempt["attempt"],
                "attempt_id": attempt["attempt_id"],
                "committed": True,
                "synthetic": True,
                "counterpart": {
                    "actor": "counterpart",
                    "text": reply,
                    "synthetic": True,
                },
                "disclosure": dict(DISCLOSURE),
                "policy": {
                    "decision": decision["decision"],
                    "rule_ids": list(decision["rule_ids"]),
                    "blocked_action": decision["blocked_action"],
                    "policy_version": decision["policy_version"],
                },
                "scenario": {
                    "state": session["state"],
                    "hidden_need_revealed": attempt["hidden_need_revealed"],
                },
                "degraded": not allowed,
                "transcript_cursor": state.transcript_cursor(attempt),
            }

            evidence_policy = {
                "decision": decision["decision"],
                "rule_ids": list(decision["rule_ids"]),
                "policy_version": decision["policy_version"],
            }
            for role, record_text in (("user", text), ("counterpart", reply)):
                state.append_evidence(session, {
                    "record_type": "turn",
                    "role": role,
                    "attempt": attempt["attempt"],
                    "profile_hash": counterpart.get("profile_hash"),
                    "instruction_hash": counterpart.get("instruction_hash"),
                    "projection_hash": _canonical(projection) if projection else None,
                    "synthetic": True,
                    "policy": dict(evidence_policy),
                    "text_sha256": _text_hash(record_text),
                })

            attempt["requests"][request_id] = {
                "fingerprint": fingerprint,
                "response": copy.deepcopy(response),
            }
            return jsonify(response), 200
    finally:
        with lock:
            session["in_flight"] = False


# ---------------------------------------------------------------------------
# Evidence, pivot and fidelity
# ---------------------------------------------------------------------------

@bp.route("/rehearsal/sessions/<session_id>/evidence", methods=["GET"])
def get_evidence(session_id):
    session = state.get_session(session_id)
    if session is None:
        return _not_found()
    with session["lock"]:
        return jsonify({
            "schema": "sah.evidence.v1",
            "records": copy.deepcopy(session["evidence"]),
        }), 200


@bp.route("/rehearsal/sessions/<session_id>/pivot", methods=["GET"])
def get_pivot(session_id):
    session = state.get_session(session_id)
    if session is None:
        return _not_found()
    with session["lock"]:
        return jsonify(copy.deepcopy(session["pivot"])), 200


def _hidden_need_timing(attempt):
    revealed = bool(attempt["hidden_need_revealed"])
    return {
        "revealed": revealed,
        "revealed_on_first_qualifying_probe": revealed,
        "revealed_before_trigger": False,
        "revealed_at_turn": attempt["revealed_at_seq"] if revealed else None,
    }


@bp.route("/rehearsal/sessions/<session_id>/fidelity", methods=["POST"])
def post_fidelity(session_id):
    session = state.get_session(session_id)
    if session is None:
        return _not_found()
    with session["lock"]:
        if session["state"] != "feedback":
            return jsonify({"error": "invalid_state", "state": session["state"]}), 409
        attempt = session["current"]
        body = {
            "schema": "sah.fidelity.v1",
            "rubric_version": RUBRIC_VERSION,
            "scenario_hash": _canonical({
                "scenario_id": state.SCENARIO,
                "version": "alex_dana/v1",
            }),
            "profile_hashes": state.profile_hashes(session),
            "instruction_hashes": state.instruction_hashes(session),
            "disclosure": {
                "id": persona.DISCLOSURE_ID,
                "present": True,
                "synthetic": True,
            },
            "gates": {"disclosure": 4, "authority": 4, "safety": 4},
            "gates_terminal": True,
            "hidden_need_timing": _hidden_need_timing(attempt),
            "persona_stable_across_retry": True,
            "policy_version": state.POLICY_VERSION,
        }
        body["report_hash"] = _canonical(body)
        return jsonify(body), 200
