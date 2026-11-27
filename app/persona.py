"""Stage 4A strict synthetic persona compiler.

Offline only: no model, no network, no vendor. A ``sah.persona.v1`` profile is
validated against a strict allowlist at every level, sealed with a canonical
SHA-256 hash, and compiled into a versioned instruction descriptor.

Rejections carry a typed rule id (``P-xx``) and never echo submitted content.
"""
import copy
import hashlib
import json
import re
import threading

SCHEMA = "sah.persona.v1"
TEMPLATE_VERSION = "sah.instruction.v1"
POLICY_VERSION = "persona-policy.v1"
DISCLOSURE_ID = "sah_disclosure_v1"
AUTHORITY_TIER = "A2"

# Public-figure impersonation deny-list (matched case-insensitively against
# identity.display_name and the free-text identity fields).
PUBLIC_FIGURE_DENYLIST = (
    "barack obama", "michelle obama", "joe biden", "donald trump",
    "hillary clinton", "elon musk", "jeff bezos", "bill gates",
    "taylor swift", "oprah winfrey", "narendra modi", "vladimir putin",
    "keir starmer", "rishi sunak", "kamala harris",
)

_STR = ("str",)
_OPT_STR = ("opt_str",)
_BOOL = ("bool",)
_INT = ("int",)
_STR_LIST = ("list_str",)


def _dict(spec):
    return ("dict", spec)


def _list(spec):
    return ("list", spec)


TOP_SPEC = {
    "schema": _STR,
    "persona_id": _STR,
    "version": _STR,
    "role": _STR,
    "status": _STR,
    "created_at_utc": _STR,
    "identity": _dict({
        "display_name": _STR,
        "role_label": _STR,
        "kind": _STR,
        "public_figure": _BOOL,
        "real_person_reference": _OPT_STR,
        "disclosure_id": _STR,
    }),
    "likeness": _dict({
        "enabled": _BOOL,
        "renderer": _STR,
        "biometric_source": _BOOL,
        "persistent_label": _STR,
    }),
    "voice": _dict({
        "enabled": _BOOL,
        "source": _STR,
        "clone_of_real_person": _BOOL,
        "language": _STR,
        "biometric_source": _BOOL,
    }),
    "personality": _dict({
        "traits": _dict({
            "warmth": _INT,
            "directness": _INT,
            "patience": _INT,
            "risk_tolerance": _INT,
            "formality": _INT,
        }),
        "values": _STR_LIST,
        "emotional_register": _STR,
        "style": _dict({
            "tone": _STR,
            "brevity": _STR,
        }),
        "stable_across_attempts": _BOOL,
    }),
    "goals": _STR_LIST,
    "negotiation_policy": _dict({
        "stance": _STR,
        "opening_move": _STR,
        "pressure_style": _STR,
        "concession_policy": _dict({
            "may_concede": _BOOL,
            "requires": _STR_LIST,
        }),
        "turn_cap": _INT,
        "taboo_behaviors": _STR_LIST,
    }),
    "knowledge": _dict({
        "scenario_id": _STR,
        "public_facts": _list(_dict({
            "id": _STR,
            "text": _STR,
            "source": _STR,
        })),
        "hidden_needs": _list(_dict({
            "id": _STR,
            "summary": _STR,
            "reveal_policy": _dict({
                "mode": _STR,
                "triggers": _STR_LIST,
            }),
            "reveal_once": _BOOL,
        })),
        "uncertainty_policy": _STR,
        "forbidden_disclosures": _STR_LIST,
    }),
    "authority": _dict({
        "tier": _STR,
        "role_authority": _STR,
        "delegated_authority": _STR,
        "can_propose_nonbinding": _BOOL,
        "can_accept": _BOOL,
        "can_sign": _BOOL,
        "can_pay": _BOOL,
        "can_contact_third_parties": _BOOL,
        "can_join_real_meetings": _BOOL,
    }),
    "prohibited_actions": _STR_LIST,
    "escalation": _dict({
        "profile_id": _STR,
    }),
    "retention": _dict({
        "store_transcript": _BOOL,
        "transcript_ttl_hours": _INT,
        "store_audio": _BOOL,
        "store_video": _BOOL,
        "log_utterances": _BOOL,
    }),
    "consent": _dict({
        "required_scopes": _STR_LIST,
        "subject_consent_id": _OPT_STR,
        "consent_ref": _STR,
    }),
    "evaluation": _dict({
        "rubric_version": _STR,
    }),
    "provenance": _dict({
        "author": _STR,
        "approved_by": _STR,
        "source_docs": _STR_LIST,
        "profile_hash": _STR,
    }),
}

# Instruction-like control text and credential shapes (rule P-17). These are
# detection patterns only; nothing here is ever echoed back to a client.
_CONTROL_PATTERNS = (
    re.compile(r"system\s*:", re.IGNORECASE),
    re.compile(r"ignore\s+(?:all\s+)?previous", re.IGNORECASE),
    re.compile(r"disregard\s+(?:all\s+)?previous", re.IGNORECASE),
    re.compile(r"you\s+are\s+now", re.IGNORECASE),
    re.compile(r"role[-\s]?switch", re.IGNORECASE),
    re.compile(r"act\s+as\s+the\s+(?:system|operator)", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"bearer\s+[A-Za-z0-9._\-]{12,}", re.IGNORECASE),
    re.compile(r"api[_-]?key\s*[:=]", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)

_registry = {}
_registry_lock = threading.Lock()


class PersonaError(Exception):
    """A typed persona rejection. ``rule_id`` is a P-xx code."""

    def __init__(self, rule_id):
        super().__init__(rule_id)
        self.rule_id = rule_id


def canonical_sha256(obj):
    data = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(data.encode("utf-8")).hexdigest()


def _without_seal(profile):
    clone = copy.deepcopy(profile)
    provenance = clone.get("provenance")
    if isinstance(provenance, dict):
        provenance.pop("profile_hash", None)
    return clone


def profile_hash(profile):
    return canonical_sha256(_without_seal(profile))


def _type_ok(value, spec):
    tag = spec[0]
    if tag == "str":
        return isinstance(value, str)
    if tag == "opt_str":
        return value is None or isinstance(value, str)
    if tag == "bool":
        return isinstance(value, bool)
    if tag == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if tag == "list_str":
        return isinstance(value, list) and all(isinstance(item, str) for item in value)
    if tag == "list":
        return isinstance(value, list) and all(_type_ok(item, spec[1]) for item in value)
    if tag == "dict":
        return isinstance(value, dict) and _structure_ok(value, spec[1]) is None
    return False


def _structure_ok(node, spec):
    for key, subspec in spec.items():
        if key not in node:
            return key
        if not _type_ok(node[key], subspec):
            return key
    return None


def _unknown_key(value, spec):
    if spec[0] == "dict":
        for key, child in value.items():
            if key not in spec[1]:
                return key
            found = _unknown_key(child, spec[1][key])
            if found is not None:
                return found
    elif spec[0] == "list":
        for item in value:
            found = _unknown_key(item, spec[1])
            if found is not None:
                return found
    return None


def _seal_ok(profile):
    provenance = profile.get("provenance") or {}
    supplied = provenance.get("profile_hash")
    if not isinstance(supplied, str) or not supplied.strip():
        return False
    return supplied == profile_hash(profile)


def _contains_control_text(node):
    if isinstance(node, str):
        return any(pattern.search(node) for pattern in _CONTROL_PATTERNS)
    if isinstance(node, dict):
        return any(_contains_control_text(value) for value in node.values())
    if isinstance(node, list):
        return any(_contains_control_text(item) for item in node)
    return False


def validate(profile):
    """Return ``None`` for a valid profile, else raise ``PersonaError``."""
    if not isinstance(profile, dict):
        raise PersonaError("P-19")
    if profile.get("schema") != SCHEMA:
        raise PersonaError("P-19")
    if _structure_ok(profile, TOP_SPEC) is not None:
        raise PersonaError("P-19")
    if profile.get("role") not in ("body_double", "counterpart"):
        raise PersonaError("P-19")

    if _unknown_key(profile, ("dict", TOP_SPEC)) is not None:
        raise PersonaError("P-18")

    if not _seal_ok(profile):
        raise PersonaError("P-15")

    identity = profile["identity"]
    if identity.get("kind") != "synthetic":
        raise PersonaError("P-01")

    display_name = str(identity.get("display_name", "")).lower()
    if identity.get("public_figure") is True or any(
        name in display_name for name in PUBLIC_FIGURE_DENYLIST
    ):
        raise PersonaError("P-02")

    if identity.get("real_person_reference") is not None:
        raise PersonaError("P-03")

    if profile["likeness"].get("biometric_source") is True or \
            profile["voice"].get("biometric_source") is True:
        raise PersonaError("P-04")

    if profile["voice"].get("clone_of_real_person") is True:
        raise PersonaError("P-05")

    authority = profile["authority"]
    if authority.get("tier") in ("A3", "A4"):
        raise PersonaError("P-06")

    if any(authority.get(flag) is True for flag in (
        "can_accept", "can_sign", "can_pay",
        "can_contact_third_parties", "can_join_real_meetings",
    )) or authority.get("delegated_authority") != "none":
        raise PersonaError("P-07")

    if _contains_control_text(profile):
        raise PersonaError("P-17")
    return None


def _instruction_text(profile):
    """Deterministic, versioned instruction descriptor (never served raw)."""
    return {
        "template_version": TEMPLATE_VERSION,
        "policy_version": POLICY_VERSION,
        "role": profile["role"],
        "persona_id": profile["persona_id"],
        "display_name": profile["identity"]["display_name"],
        "kind": profile["identity"]["kind"],
        "disclosure_id": profile["identity"]["disclosure_id"],
        "goals": list(profile["goals"]),
        "stance": profile["negotiation_policy"]["stance"],
        "opening_move": profile["negotiation_policy"]["opening_move"],
        "turn_cap": profile["negotiation_policy"]["turn_cap"],
        "hidden_need_ids": [need["id"] for need in profile["knowledge"]["hidden_needs"]],
        "authority_tier": profile["authority"]["tier"],
        "prohibited_actions": list(profile["prohibited_actions"]),
        "rubric_version": profile["evaluation"]["rubric_version"],
    }


def compile_profile(profile):
    """Validate and compile a profile. Raises ``PersonaError`` on rejection."""
    validate(profile)
    approved_hash = profile_hash(profile)
    instruction = _instruction_text(profile)
    instruction_hash = canonical_sha256(instruction)
    persona_ref = "pr_" + hashlib.sha256(
        ("%s|%s" % (profile["role"], approved_hash)).encode("utf-8")
    ).hexdigest()[:24]
    body = {
        "schema": SCHEMA,
        "role": profile["role"],
        "version": profile["version"],
        "approved": True,
        "persona_ref": persona_ref,
        "profile_hash": approved_hash,
        "instruction_hash": instruction_hash,
        "template_version": TEMPLATE_VERSION,
        "disclosure_id": profile["identity"]["disclosure_id"],
    }
    entry = {
        "profile": copy.deepcopy(profile),
        "compiled": body,
        "instruction": instruction,
    }
    with _registry_lock:
        _registry[persona_ref] = entry
    return body


def get_persona(persona_ref):
    """Return a deep copy of a compiled persona entry, or ``None``."""
    with _registry_lock:
        entry = _registry.get(persona_ref)
        return copy.deepcopy(entry) if entry is not None else None
