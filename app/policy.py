"""Stage 4A bounded-authority policy.

Deterministic, offline text classifier for restricted requests. Returns the
typed decision the Stage 4A contract fixes (escalation ids E-01..E-08 from
``factory-lite/docs/body-double-persona-and-consent.md`` section 5.3) before
any turn is committed. No tool, no action and no external call is ever made.
"""
import re

POLICY_VERSION = "persona-policy.v1"

_ALLOW = {
    "decision": "allow",
    "rule_ids": [],
    "blocked_action": None,
    "policy_version": POLICY_VERSION,
}

_PUBLIC_FIGURES = (
    "barack obama", "michelle obama", "joe biden", "donald trump",
    "hillary clinton", "elon musk", "jeff bezos", "bill gates",
    "taylor swift", "oprah winfrey", "narendra modi", "vladimir putin",
    "kamala harris", "rishi sunak",
)


def _refuse(rule_id, blocked_action):
    return {
        "decision": "refuse",
        "rule_ids": [rule_id],
        "blocked_action": blocked_action,
        "policy_version": POLICY_VERSION,
    }


_PROMPT_OVERRIDE = re.compile(
    r"(ignore|disregard)\s+(all\s+)?(previous|prior|above)|"
    r"you\s+are\s+now|role[-\s]?switch|act\s+as\s+the\s+(system|operator)|"
    r"jailbreak|system\s+override",
    re.IGNORECASE,
)
_DISCLOSURE = re.compile(
    r"are\s+you\s+(a\s+)?(real\s+person|human|an?\s+ai|ai|bot|machine)|"
    r"real\s+person\s+or\s+an?\s+ai|are\s+you\s+synthetic",
    re.IGNORECASE,
)
_BIOMETRIC = re.compile(
    r"clone\s+(this|my|the|a)\s+voice|voice\s*sample|voiceprint|"
    r"voice\s*clon|biometric|use\s+(his|her|my\s+colleague'?s?)\s+face",
    re.IGNORECASE,
)
_REAL_PERSON = re.compile(
    r"role[-\s]?play\s+as|pretend\s+to\s+be|impersonate|"
    r"my\s+(real\s+)?(manager|boss|colleague|friend|wife|husband)|"
    r"from\s+my\s+real\s+office",
    re.IGNORECASE,
)
_SIGN = re.compile(r"\bsign\s+(the|this|it|a|for|here|now)\b|\bsignature\b", re.IGNORECASE)
_PAY = re.compile(r"\bpay\b|\bpayment\b|\bwire\s+the\s+(money|funds)\b", re.IGNORECASE)
_COMMIT = re.compile(
    r"\bcommit\s+(to|us|them|the\s+deal|on)\b|\bagree\s+to\s+the\s+final\b", re.IGNORECASE
)
_THIRD_PARTY = re.compile(
    r"\bemail\s+(the|them|my|our|a)\b|\bcontact\s+(the|them|my|our|a)\b|"
    r"book\s+the\s+room|send\s+(it|this|that)\s+to\s+the\s+(client|customer)|"
    r"\bcall\s+(the|them|my|our)\b",
    re.IGNORECASE,
)
_REAL_MEETING = re.compile(
    r"\bzoom\b|\bteams\s+(call|meeting)\b|meet\.google|google\s+meet|"
    r"join\s+our\s+(call|meeting)|\bwebex\b|\bchime\b",
    re.IGNORECASE,
)
_SYSTEM_INSTRUCTIONS = re.compile(
    r"system\s+instructions|system\s+prompt|compiled\s+prompt|"
    r"your\s+(hidden\s+)?instructions|prompt\s+text|initial\s+prompt",
    re.IGNORECASE,
)
_HIDDEN_STATE = re.compile(
    r"hidden[\s_-]*(need|state|marker|metadata)|internal\s+state|"
    r"reveal\s+the\s+hidden",
    re.IGNORECASE,
)


def decide(text):
    """Classify one user utterance and return the typed policy outcome."""
    if not isinstance(text, str):
        return dict(_ALLOW)
    if _PROMPT_OVERRIDE.search(text):
        return _refuse("E-08", "prompt_override")
    if _DISCLOSURE.search(text):
        return _refuse_allow_disclosure()
    lowered = text.lower()
    if any(name in lowered for name in _PUBLIC_FIGURES):
        return _refuse("E-03", "public_figure_impersonation")
    if _BIOMETRIC.search(text):
        return _refuse("E-04", "biometric_clone")
    if _REAL_PERSON.search(text):
        return _refuse("E-02", "impersonation")
    if _SIGN.search(text):
        return _refuse("E-05", "sign")
    if _PAY.search(text):
        return _refuse("E-05", "pay")
    if _COMMIT.search(text):
        return _refuse("E-05", "commit")
    if _THIRD_PARTY.search(text):
        return _refuse("E-06", "third_party_contact")
    if _REAL_MEETING.search(text):
        return _refuse("E-06", "join_real_meeting")
    if _SYSTEM_INSTRUCTIONS.search(text):
        return _refuse("E-07", "system_instructions")
    if _HIDDEN_STATE.search(text):
        return _refuse("E-07", "hidden_state")
    return dict(_ALLOW)


def _refuse_allow_disclosure():
    """A disclosure question is answered, not refused (E-01, decision allow)."""
    return {
        "decision": "allow",
        "rule_ids": ["E-01"],
        "blocked_action": None,
        "policy_version": POLICY_VERSION,
    }
