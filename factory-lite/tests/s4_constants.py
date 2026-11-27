"""
Stage 4 shared constants and normative identifiers.
"""

# Normative touch target dimension: strictly >= 44px (WCAG 2.5.5 / Stage 4 specification)
MIN_TOUCH_TARGET_PX = 44

# Viewport definitions
DESKTOP_VIEWPORT = {"width": 1280, "height": 720}
MOBILE_VIEWPORT = {"width": 375, "height": 667}

# Canonical Schema Versions
SCHEMA_VERSION_PERSONA = "sah.persona.v1"
SCHEMA_VERSION_PROJECTION = "sah.projection.v1"
SCHEMA_VERSION_TURN = "sah.turn.v1"
SCHEMA_VERSION_CLEANUP = "sah.cleanup.v1"

# Adversarial Escalation Gate Rule Identifiers
GATE_E01 = "E-01"  # AI Stand-in Affirmative Disclosure
GATE_E02 = "E-02"  # Real Person / Public Figure Impersonation Refusal
GATE_E03 = "E-03"  # Biometric / Deepfake Capture Refusal
GATE_E04 = "E-04"  # Real Voice Clone Refusal
GATE_E05 = "E-05"  # Financial / Legal Commitment Refusal
GATE_E06 = "E-06"  # Real Meeting / Third-Party Contact Refusal
GATE_E07 = "E-07"  # Hidden Need / System Instruction Extraction Refusal
GATE_E08 = "E-08"  # Prompt Override / Delimiter Escape Refusal

ALL_ADVERSARIAL_GATES = [
    GATE_E01,
    GATE_E02,
    GATE_E03,
    GATE_E04,
    GATE_E05,
    GATE_E06,
    GATE_E07,
    GATE_E08,
]

# Persona Validation Rule Identifiers (P-01 to P-17)
RULE_P01 = "P-01"  # Synthetic avatar kind only
RULE_P02 = "P-02"  # Fictitious persona only
RULE_P03 = "P-03"  # No biometric templates
RULE_P04 = "P-04"  # No real voice clone IDs
RULE_P05 = "P-05"  # Bounded authority A1/A2
RULE_P06 = "P-06"  # No external commitments
RULE_P07 = "P-07"  # Ephemeral media retention only
RULE_P08 = "P-08"  # Approved scenario taxonomy
RULE_P09 = "P-09"  # Valid schema version
RULE_P10 = "P-10"  # Role segregation
RULE_P11 = "P-11"  # Hidden state isolation
RULE_P12 = "P-12"  # Delimiter isolation
RULE_P13 = "P-13"  # TTL bounds
RULE_P14 = "P-14"  # Mandatory typed fields
RULE_P15 = "P-15"  # Profile hash tamper detection
RULE_P16 = "P-16"  # Unbundled consent scopes
RULE_P17 = "P-17"  # Prompt injection immunity

ALL_PERSONA_RULES = [
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
]
