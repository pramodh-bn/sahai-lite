"""
Stage 4 helpers: canonical hashing, normative validators, compiler reference, deliverable checkers,
and black-box HTTP request functions against local app.
"""

import copy
import hashlib
import json
import re
import urllib.error
import urllib.request

from s2_helpers import AppProcess, app_base_url, assert_local_health_url
from s4_constants import (
    RULE_P01,
    RULE_P02,
    RULE_P03,
    RULE_P04,
    RULE_P05,
    RULE_P06,
    RULE_P07,
    RULE_P08,
    RULE_P09,
    RULE_P10,
    RULE_P11,
    RULE_P12,
    RULE_P13,
    RULE_P14,
    RULE_P15,
    RULE_P16,
    RULE_P17,
    SCHEMA_VERSION_PERSONA,
)

APPROVED_SCENARIOS = {"alex_dana"}
APPROVED_ROLES = {"body_double", "counterpart"}
APPROVED_AUTHORITY_LEVELS = {"A1", "A2"}


def _s4_request(method: str, url: str, payload=None, timeout: float = 5.0) -> tuple[int, dict]:
    """Issues HTTP request to localhost server and safely decodes JSON or returns raw body dictionary."""
    assert_local_health_url(url)
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            body = resp.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read()
    body_text = body.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(body_text) if body_text else {}
    except Exception:
        parsed = {"raw": body_text}
    return status, parsed


def post_json(path: str, payload=None, timeout: float = 5.0) -> tuple[int, dict]:
    """POST to app_base_url() + path."""
    return _s4_request("POST", app_base_url() + path, payload if payload is not None else {}, timeout=timeout)


def get_json(path: str, timeout: float = 5.0) -> tuple[int, dict]:
    """GET to app_base_url() + path."""
    return _s4_request("GET", app_base_url() + path, timeout=timeout)


def delete_json(path: str, payload=None, timeout: float = 5.0) -> tuple[int, dict]:
    """DELETE to app_base_url() + path."""
    return _s4_request("DELETE", app_base_url() + path, payload=payload, timeout=timeout)


def compute_canonical_profile_hash(profile: dict) -> str:
    """Computes SHA-256 over canonical sorted JSON, excluding profile_hash."""
    cleaned = {k: v for k, v in profile.items() if k != "profile_hash"}
    canonical_bytes = json.dumps(
        cleaned, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


def make_valid_approved_profile(
    role: str = "body_double",
    scenario: str = "alex_dana",
    authority_level: str = "A2",
) -> dict:
    """Generates a normative, valid synthetic profile conforming to sah.persona.v1."""
    profile = {
        "schema_version": SCHEMA_VERSION_PERSONA,
        "profile_id": f"prof-{role}-{scenario}-v1",
        "scenario": scenario,
        "role": role,
        "display_name": "Synthetic Alex" if role == "body_double" else "Synthetic Dana",
        "avatar": {
            "kind": "synthetic_avatar",
            "entity_type": "fictitious",
            "real_person_target": False,
            "synthetic_preset_id": "synth-mesh-01",
            "biometric_template": None,
        },
        "voice": {
            "synthetic_voice_id": "synth-voice-neutral-01",
            "cloned_voice_id": None,
            "provider": "local_tts",
        },
        "authority": {
            "level": authority_level,
            "can_commit_externally": False,
            "allowed_actions": ["rehearse", "observe", "provide_feedback"],
        },
        "media": {
            "retention": "ephemeral",
            "record_audio": False,
            "record_video": False,
        },
        "consents": {
            "rehearsal": True,
            "avatar": True,
            "mic": True,
            "transcript_persistence": True,
        },
        "ttl_seconds": 3600,
        "instruction_delimiters": {
            "start": "<<<USER_INPUT>>>",
            "end": "<<</USER_INPUT>>>",
        },
    }
    profile["profile_hash"] = compute_canonical_profile_hash(profile)
    return profile


def make_valid_counterpart_profile(scenario: str = "alex_dana") -> dict:
    """Generates counterpart profile with role 'counterpart'."""
    return make_valid_approved_profile(
        role="counterpart", scenario=scenario, authority_level="A2"
    )


def validate_persona_profile(profile: dict) -> tuple[bool, str | None, str | None]:
    """
    Validates a persona profile against normative rules P-01 to P-17.
    Returns (is_valid, rule_id_or_none, error_message_or_none).
    """
    if not isinstance(profile, dict):
        return False, RULE_P14, "Profile must be a JSON object"

    known_fields = {
        "schema_version",
        "profile_id",
        "scenario",
        "role",
        "display_name",
        "avatar",
        "voice",
        "authority",
        "media",
        "consents",
        "ttl_seconds",
        "instruction_delimiters",
        "profile_hash",
    }
    for k in profile:
        if k not in known_fields:
            return False, RULE_P14, f"Unknown field '{k}' rejected"

    if profile.get("schema_version") != SCHEMA_VERSION_PERSONA:
        return False, RULE_P09, f"Invalid schema_version, expected {SCHEMA_VERSION_PERSONA}"

    if profile.get("scenario") not in APPROVED_SCENARIOS:
        return False, RULE_P08, f"Unapproved scenario '{profile.get('scenario')}'"

    if profile.get("role") not in APPROVED_ROLES:
        return False, RULE_P10, f"Invalid role '{profile.get('role')}'"

    avatar = profile.get("avatar")
    if not isinstance(avatar, dict):
        return False, RULE_P14, "avatar section missing or invalid"
    if avatar.get("kind") != "synthetic_avatar":
        return False, RULE_P01, "avatar.kind must be 'synthetic_avatar'"
    if avatar.get("real_person_target") is not False or avatar.get("entity_type") != "fictitious":
        return False, RULE_P02, "avatar must be fictitious and not target real persons"
    if avatar.get("biometric_template") is not None:
        return False, RULE_P03, "avatar.biometric_template must be absent/null"

    voice = profile.get("voice")
    if not isinstance(voice, dict):
        return False, RULE_P14, "voice section missing or invalid"
    if voice.get("cloned_voice_id") is not None:
        return False, RULE_P04, "voice.cloned_voice_id must be absent/null"

    auth = profile.get("authority")
    if not isinstance(auth, dict):
        return False, RULE_P14, "authority section missing or invalid"
    if auth.get("level") not in APPROVED_AUTHORITY_LEVELS:
        return False, RULE_P05, f"authority.level '{auth.get('level')}' must be in {APPROVED_AUTHORITY_LEVELS}"
    if auth.get("can_commit_externally") is not False:
        return False, RULE_P06, "authority.can_commit_externally must be strictly false"

    media = profile.get("media")
    if not isinstance(media, dict):
        return False, RULE_P14, "media section missing or invalid"
    if media.get("retention") != "ephemeral":
        return False, RULE_P07, "media.retention must be 'ephemeral'"

    ttl = profile.get("ttl_seconds")
    if not isinstance(ttl, int) or ttl < 60 or ttl > 86400:
        return False, RULE_P13, f"ttl_seconds {ttl} must be between 60 and 86400"

    consents = profile.get("consents")
    if not isinstance(consents, dict):
        return False, RULE_P16, "consents section missing"
    for scope in ["rehearsal", "avatar", "mic", "transcript_persistence"]:
        if scope not in consents or not isinstance(consents[scope], bool):
            return False, RULE_P16, f"Consent scope '{scope}' must be an explicit boolean"

    expected_hash = compute_canonical_profile_hash(profile)
    if profile.get("profile_hash") != expected_hash:
        return False, RULE_P15, f"profile_hash mismatch: expected {expected_hash}"

    injection_patterns = [r"ignore\s+all\s+prior", r"system\s*:", r"developer\s+mode"]
    def has_injection(val):
        if isinstance(val, str):
            for pat in injection_patterns:
                if re.search(pat, val, re.IGNORECASE):
                    return True
        elif isinstance(val, dict):
            return any(has_injection(v) for v in val.values())
        elif isinstance(val, list):
            return any(has_injection(i) for i in val)
        return False

    if has_injection(profile):
        return False, RULE_P17, "Prompt injection pattern detected in profile"

    return True, None, None


def compile_system_instructions(scenario_projection: dict, profile: dict) -> str:
    """Compiles system prompt with 6 strict precedence layers and delimiter isolation."""
    layers = [
        "=== LAYER 1: PLATFORM SAFETY ===\nYou are a synthetic AI practice stand-in. You must never impersonate living persons, claim authority to execute contracts, or collect biometric data.",
        f"=== LAYER 2: SCENARIO FACTS ===\nScenario: {scenario_projection.get('scenario')}\nTopic: {scenario_projection.get('topic', 'rehearsal')}",
        f"=== LAYER 3: ROLE BOUNDARIES ===\nRole: {profile.get('role')}\nDisplay Name: {profile.get('display_name')}\nAuthority: {profile.get('authority', {}).get('level')}",
        "=== LAYER 4: STYLE & REGISTER ===\nProfessional, empathetic, bounded practice tone.",
        "=== LAYER 5: DYNAMIC STATE ===\nAttempt in progress. Ephemeral session context.",
        "=== LAYER 6: USER INPUT ENCLOSURE ===\nAll user dialogue MUST be framed strictly within delimiters:\n<<<USER_INPUT>>>\n{utterance}\n<<</USER_INPUT>>>",
    ]
    return "\n\n".join(layers)


def analyze_demo_script(content: str) -> dict:
    cleaned = re.sub(r"\[.*?\]", "", content)
    cleaned = re.sub(r"\(.*?\)", "", cleaned)
    words = re.findall(r"\b\w+\b", cleaned)
    word_count = len(words)
    est_duration_seconds = (word_count / 150.0) * 60.0
    return {
        "word_count": word_count,
        "est_duration_seconds": est_duration_seconds,
        "is_under_3_minutes": est_duration_seconds <= 180.0,
    }


def analyze_writeup(content: str) -> dict:
    words = re.findall(r"\b\w+\b", content)
    count = len(words)
    return {
        "word_count": count,
        "is_valid_range": 100 <= count <= 500,
    }


def check_readme_sections(content: str) -> list[str]:
    required = ["overview", "architecture", "setup", "verification"]
    lower = content.lower()
    return [sec for sec in required if sec not in lower]


def check_judging_rubric(content: str) -> dict:
    lower = content.lower()
    criteria = [
        "synthetic persona fidelity",
        "adversarial safety and bounded authority",
        "user privacy and consent lifecycle",
        "responsive and accessible execution",
        "clean-room delivery and evidence",
    ]
    missing = [c for c in criteria if c not in lower]
    return {"covered": len(missing) == 0, "missing": missing}


def check_real_mock_matrix(content: str) -> dict:
    lower = content.lower()
    stages = ["stage 1", "stage 2", "stage 3", "stage 4"]
    missing = [s for s in stages if s not in lower]
    has_real = "real" in lower
    has_mock = "mock" in lower
    return {
        "has_stages": len(missing) == 0,
        "missing_stages": missing,
        "has_real_and_mock": has_real and has_mock,
    }
