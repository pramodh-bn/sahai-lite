"""Shared Stage 4B consent schema constants (no side effects)."""

SCHEMA = "sah.consent.v1"
POLICY_VERSION = "consent.v1"
SCOPES = (
    "rehearsal",
    "avatar",
    "mic",
    "transcript_save",
    "research",
    "subject_consent",
)
NON_APPLICABLE = ("subject_consent",)


def new_consent_record():
    """Every scope starts explicitly denied; only subject consent is N/A in v1."""
    return {
        scope: {
            "granted": False,
            "applicable": scope not in NON_APPLICABLE,
            "recorded_at_utc": None,
        }
        for scope in SCOPES
    }
