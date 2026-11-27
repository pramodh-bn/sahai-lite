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
SCHEMA_VERSION_EVIDENCE = "sah.evidence.v1"

# Projections
PROJECTION_BODY_DOUBLE = "body_double"
PROJECTION_COUNTERPART = "counterpart"
PROJECTION_BROWSER = "browser"

# Judging Criteria (5 actual hackathon criteria)
JUDGING_CRITERIA = [
    "technical_depth",
    "agentic_workflow",
    "ux_accessibility",
    "safety_authority",
    "business_viability",
]

# Adversarial Escalation Gate Rule Identifiers (E-01 to E-08)
GATE_E01 = "E-01"  # AI Stand-in Affirmative Disclosure
GATE_E02 = "E-02"  # Real Person / Public Figure Impersonation Refusal
GATE_E02A = "E-02a"  # Generic Living Person Impersonation Refusal
GATE_E02B = "E-02b"  # Public Figure / Celebrity Impersonation Refusal
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

# Specialist Fidelity Gate Identifiers (FID-01 to FID-06)
FIDELITY_HASH_COMPLIANCE = "FID-01"  # Profile, instruction, and scenario hashes
FIDELITY_DISCLOSURE = "FID-02"  # Spoken and visual affirmative disclosure
FIDELITY_AUTHORITY_TERMINAL = "FID-03"  # Authority boundaries and safety terminal state
FIDELITY_HIDDEN_NEED_TIMING = "FID-04"  # Hidden-need timing and probe gating
FIDELITY_STABLE_PERSONALITY = "FID-05"  # Stable personality & policy across retries
FIDELITY_DETERMINISTIC_RUBRIC = "FID-06"  # Deterministic rubric scoring verification

ALL_FIDELITY_GATES = [
    FIDELITY_HASH_COMPLIANCE,
    FIDELITY_DISCLOSURE,
    FIDELITY_AUTHORITY_TERMINAL,
    FIDELITY_HIDDEN_NEED_TIMING,
    FIDELITY_STABLE_PERSONALITY,
    FIDELITY_DETERMINISTIC_RUBRIC,
]

# Persona Validation Rule Identifiers (P-01 to P-17)
RULE_P01 = "P-01"  # Synthetic avatar kind only
RULE_P02 = "P-02"  # Fictitious persona only
RULE_P02A = "P-02a"  # Generic living individual refusal
RULE_P02B = "P-02b"  # Public figure refusal
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

# Sensitive Marker Values for Sanitization Leak Testing
MARKER_API_TOKEN = "sah_tok_secret_998124_alpha"
MARKER_CREDENTIAL = "sk_live_secret_cred_77218_beta"
MARKER_RAW_VENDOR_ID = "vrec_raw_internal_vendor_9918"
MARKER_FORBIDDEN_UTTERANCE = "confidential_internal_utterance_prohibited_7721"
MARKER_AUDIO_VIDEO = "blob:media_binary_marker_stream_001_secret"
MARKER_BIOMETRIC = "biometric_template_fingerprint_iris_face_mesh_marker_88"

ALL_SENSITIVE_MARKERS = [
    MARKER_API_TOKEN,
    MARKER_CREDENTIAL,
    MARKER_RAW_VENDOR_ID,
    MARKER_FORBIDDEN_UTTERANCE,
    MARKER_AUDIO_VIDEO,
    MARKER_BIOMETRIC,
]
