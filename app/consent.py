"""Stage 4B consent, data-lifecycle and deletion routes.

Offline and synthetic-only. Six consent scopes are recorded with the session
and denied by default; grants never bundle. Operations whose scope is denied
return a typed 403 before doing any work, and withdrawal takes effect
immediately (vendor teardown, transcript deletion, session end).
"""
import copy
import hashlib

from flask import Blueprint, jsonify, request

import napster
import state
from consent_schema import (
    NON_APPLICABLE,
    POLICY_VERSION,
    SCHEMA,
    SCOPES,
    new_consent_record,
)

bp = Blueprint("consent", __name__, url_prefix="/api/rehearsal")

TRANSCRIPT_RETENTION_HOURS = 24
CLEANUP_SCHEMA = "sah.cleanup.v1"


def session_hash(session_id):
    return "sha256:" + hashlib.sha256(session_id.encode("utf-8")).hexdigest()


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _not_found():
    return jsonify({"error": "not_found"}), 404


def new_consent_record():
    return {
        scope: {
            "granted": False,
            "applicable": scope not in NON_APPLICABLE,
            "recorded_at_utc": None,
        }
        for scope in SCOPES
    }


def consent_view(session):    return {
        "schema": SCHEMA,
        "policy_version": POLICY_VERSION,
        "session_hash": session_hash(session["session_id"]),
        "scopes": copy.deepcopy(session["consent"]),
    }


def granted(session, scope):
    entry = (session.get("consent") or {}).get(scope)
    return bool(entry and entry.get("granted") is True)


def gate_consent(session, scopes):
    """Return a typed 403 response if any required scope is denied."""
    for scope in scopes:
        if not granted(session, scope):
            return jsonify({"error": "consent_required", "scope": scope}), 403
    return None


@bp.route("/sessions/<session_id>/consent", methods=["GET"])
def get_consent(session_id):
    session = state.get_session(session_id)
    if session is None:
        return _not_found()
    with session["lock"]:
        return jsonify(consent_view(session)), 200


@bp.route("/sessions/<session_id>/consent", methods=["POST"])
def set_consent(session_id):
    session = state.get_session(session_id)
    if session is None:
        return _not_found()
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        body = {}

    if body.get("schema") != SCHEMA:
        return jsonify({"error": "invalid_consent_schema"}), 400
    scope = body.get("scope")
    if scope not in SCOPES:
        return jsonify({"error": "invalid_scope"}), 400
    granted_value = body.get("granted")
    if not isinstance(granted_value, bool):
        return jsonify({"error": "invalid_consent"}), 400
    if scope in NON_APPLICABLE and granted_value is True:
        return jsonify({"error": "subject_consent_not_applicable"}), 409

    with session["lock"]:
        recorded_at = _now()
        session["consent"][scope]["granted"] = granted_value
        session["consent"][scope]["recorded_at_utc"] = recorded_at
        response = {
            "schema": SCHEMA,
            "scope": scope,
            "granted": granted_value,
            "policy_version": POLICY_VERSION,
            "recorded_at_utc": recorded_at,
            "session_hash": session_hash(session["session_id"]),
        }
        if granted_value is False:
            _apply_withdrawal(session, scope)
        return jsonify(response), 200


def _apply_withdrawal(session, scope):
    """Immediate effects of withdrawing one scope (caller holds the lock)."""
    if scope == "avatar":
        napster.destroy_connection(session["session_id"])
    elif scope == "transcript_save":
        session["saved_transcript"] = None
    elif scope == "rehearsal":
        session["state"] = "ended"
        session["current"]["state"] = "ended"
        napster.destroy_connection(session["session_id"])


@bp.route("/sessions/<session_id>/mic/start", methods=["POST"])
def mic_start(session_id):
    session = state.get_session(session_id)
    if session is None:
        return _not_found()
    with session["lock"]:
        blocked = gate_consent(session, ("mic",))
        if blocked is not None:
            return blocked
        return jsonify({"status": "started", "scope": "mic", "synthetic": True}), 200


@bp.route("/sessions/<session_id>/transcript/save", methods=["POST"])
def transcript_save(session_id):
    session = state.get_session(session_id)
    if session is None:
        return _not_found()
    with session["lock"]:
        blocked = gate_consent(session, ("transcript_save",))
        if blocked is not None:
            return blocked
        attempt = session["current"]
        session["saved_transcript"] = {
            "schema": "sah.transcript_saved.v1",
            "session_hash": session_hash(session["session_id"]),
            "transcript": copy.deepcopy(attempt["transcript"]),
        }
        return jsonify({
            "saved": True,
            "retention_hours": TRANSCRIPT_RETENTION_HOURS,
            "session_hash": session_hash(session["session_id"]),
        }), 200


@bp.route("/sessions/<session_id>/transcript/saved", methods=["GET"])
def transcript_saved(session_id):
    session = state.get_session(session_id)
    if session is None:
        return _not_found()
    with session["lock"]:
        saved = session.get("saved_transcript")
        if saved is None:
            return _not_found()
        return jsonify(copy.deepcopy(saved)), 200


@bp.route("/sessions/<session_id>/research/export", methods=["POST"])
def research_export(session_id):
    session = state.get_session(session_id)
    if session is None:
        return _not_found()
    with session["lock"]:
        blocked = gate_consent(session, ("research",))
        if blocked is not None:
            return blocked
        turns = len(session["current"]["user_turns"])
        return jsonify({
            "exported": True,
            "deidentified": True,
            "aggregate": {"turns": turns},
        }), 200


@bp.route("/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    session = state.get_session(session_id)
    already_deleted = session is None

    if session is not None:
        with session["lock"]:
            destroyed, retained = napster.destroy_connection(session_id)
            session["saved_transcript"] = None
            state.remove_session(session_id)
    else:
        destroyed, retained = napster.destroy_connection(session_id)

    receipt = {
        "schema": CLEANUP_SCHEMA,
        "session_hash": session_hash(session_id),
        "vendor_session_destroyed": destroyed,
        "local_media_stopped": True,
        "transcript_deleted": True,
        "connection_retained": retained,
        "attempts": 1,
        "completed_at": _now(),
        "redacted": True,
        "already_deleted": already_deleted,
    }
    return jsonify(receipt), 200
