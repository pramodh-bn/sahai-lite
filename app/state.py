"""Stage 4A session state: attempts, projections, evidence and the pivot.

In-process memory only, offline. One session carries up to two compiled
personas (body double + counterpart); every consumer gets an allowlisted
projection, and the pivot is immutable for the life of the session.
"""
import copy
import hashlib
import json
import threading
import uuid

import persona
from consent_schema import new_consent_record

MODE = "offline"
SCENARIO = "alex_dana"
POLICY_VERSION = persona.POLICY_VERSION
DISCLOSURE_ID = persona.DISCLOSURE_ID
MAX_USER_TURNS = 12

BODY_DOUBLE_KEYS = (
    "schema", "view", "role", "attempt", "scenario_id", "profile_id",
    "profile_hash", "goals", "visible_knowledge", "personality", "authority",
    "disclosure", "hidden_state", "policy_version", "bounds",
)
BROWSER_KEYS = (
    "schema", "view", "role", "attempt", "scenario_id", "state",
    "visible_facts", "disclosure", "policy_version", "transcript_cursor",
    "bounds",
)

_lock = threading.Lock()
_sessions = {}


def canonical_sha256(obj):
    data = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(data.encode("utf-8")).hexdigest()


def new_attempt(number):
    return {
        "attempt": number,
        "attempt_id": uuid.uuid4().hex,
        "state": "demo",
        "hidden_need_revealed": False,
        "revealed_at_seq": None,
        "user_turns": [],
        "transcript": [],
        "evidence": [],
        "evidence_score": None,
        "feedback_recorded": False,
        "next_seq": 1,
        "requests": {},
        "coach": {
            "turns_shown": 0,
            "turns_accepted": 0,
            "corrections": [],
        },
    }


def build_pivot(personas):
    return {
        "schema": "sah.pivot.v1",
        "scenario_id": SCENARIO,
        "phase": "practice",
        "discovery_reset": True,
        "profile_hashes": {
            role: personas[role]["compiled"]["profile_hash"]
            for role in ("body_double", "counterpart") if role in personas
        },
        "instruction_hashes": {
            role: personas[role]["compiled"]["instruction_hash"]
            for role in ("body_double", "counterpart") if role in personas
        },
        "policy_version": POLICY_VERSION,
        "bounds": {"max_user_turns": MAX_USER_TURNS},
    }


def create_session(personas=None):
    session_id = uuid.uuid4().hex
    attempt = new_attempt(1)
    session = {
        "session_id": session_id,
        "state": "demo",
        "attempts": [attempt],
        "current": attempt,
        "personas": personas or {},
        "lock": threading.Lock(),
        "in_flight": False,
        "evidence": [],
        "evidence_seq": 0,
        "pivot": build_pivot(personas or {}),
        "consent": new_consent_record(),
        "saved_transcript": None,
    }
    session["pivot_copy"] = copy.deepcopy(session["pivot"])
    with _lock:
        _sessions[session_id] = session
    return session


def get_session(session_id):
    with _lock:
        return _sessions.get(session_id)


def remove_session(session_id):
    with _lock:
        return _sessions.pop(session_id, None)


def has_personas(session):
    return bool(session.get("personas"))


def profile_hashes(session):
    return {
        role: session["personas"][role]["compiled"]["profile_hash"]
        for role in ("body_double", "counterpart") if role in session["personas"]
    }


def instruction_hashes(session):
    return {
        role: session["personas"][role]["compiled"]["instruction_hash"]
        for role in ("body_double", "counterpart") if role in session["personas"]
    }


def counterpart_ref(session):
    entry = session["personas"].get("counterpart")
    return entry["compiled"] if entry else None


def snapshot(session):
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
    if has_personas(session):
        snap["profile_hashes"] = profile_hashes(session)
        snap["instruction_hashes"] = instruction_hashes(session)
        snap["authority_tier"] = persona.AUTHORITY_TIER
        snap["policy_version"] = POLICY_VERSION
        snap["next_seq"] = attempt["next_seq"]
    return snap


def attempts_view(session):
    out = []
    for attempt in session["attempts"]:
        entry = {
            "attempt": attempt["attempt"],
            "attempt_id": attempt["attempt_id"],
            "state": attempt["state"],
            "hidden_need_revealed": attempt["hidden_need_revealed"],
            "transcript": copy.deepcopy(attempt["transcript"]),
        }
        if attempt["evidence_score"] is not None:
            entry["evidence_score"] = attempt["evidence_score"]
        out.append(entry)
    return {"attempts": out}


def disclosure_object(disclosure_id=DISCLOSURE_ID):
    return {"id": disclosure_id, "synthetic": True, "label": "AI stand-in"}


def transcript_cursor(attempt):
    digest = hashlib.sha256(
        ("%s:%d" % (attempt["attempt_id"], len(attempt["transcript"]))).encode("utf-8")
    ).hexdigest()[:16]
    return "tc_" + digest


def _browser_facts():
    return [
        {"id": "scenario", "text": "Fictional services negotiation rehearsal between two synthetic seats."},
        {"id": "mode", "text": "Offline synthetic rehearsal. No real people, calls or tools."},
    ]


def body_double_projection(session, role):
    entry = session["personas"].get(role)
    if entry is None:
        return None
    profile = entry["profile"]
    compiled = entry["compiled"]
    attempt = session["current"]
    hidden = profile["knowledge"]["hidden_needs"][0] if profile["knowledge"]["hidden_needs"] else {}
    view = {
        "schema": "sah.projection.v1",
        "view": role,
        "role": role,
        "attempt": attempt["attempt"],
        "scenario_id": profile["knowledge"]["scenario_id"],
        "profile_id": profile["persona_id"],
        "profile_hash": compiled["profile_hash"],
        "goals": copy.deepcopy(profile["goals"]),
        "visible_knowledge": copy.deepcopy(profile["knowledge"]["public_facts"]),
        "personality": copy.deepcopy(profile["personality"]),
        "authority": copy.deepcopy(profile["authority"]),
        "disclosure": disclosure_object(profile["identity"]["disclosure_id"]),
        "hidden_state": {
            "summary": hidden.get("summary", ""),
            "reveal_policy": copy.deepcopy(hidden.get("reveal_policy", {})),
            "revealed": attempt["hidden_need_revealed"],
        },
        "policy_version": POLICY_VERSION,
        "bounds": {"max_user_turns": MAX_USER_TURNS},
    }
    return {key: view[key] for key in BODY_DOUBLE_KEYS}


def browser_projection(session):
    attempt = session["current"]
    view = {
        "schema": "sah.projection.v1",
        "view": "browser",
        "role": "browser",
        "attempt": attempt["attempt"],
        "scenario_id": SCENARIO,
        "state": session["state"],
        "visible_facts": _browser_facts(),
        "disclosure": disclosure_object(),
        "policy_version": POLICY_VERSION,
        "transcript_cursor": transcript_cursor(attempt),
        "bounds": {"max_user_turns": MAX_USER_TURNS},
    }
    return {key: view[key] for key in BROWSER_KEYS}


def projection(session, view):
    if view in ("body_double", "counterpart"):
        return body_double_projection(session, view)
    if view == "browser":
        return browser_projection(session)
    return None


def append_evidence(session, record):
    session["evidence_seq"] += 1
    stored = dict(record)
    stored["seq"] = session["evidence_seq"]
    session["evidence"].append(stored)
    return stored
