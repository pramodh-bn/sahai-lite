"""
Stage 4 helpers: canonical hashing, normative validators, compiler reference,
deliverable checkers, process controller with log capture, test-owned fake vendor cleanup boundary,
and black-box HTTP request functions against local app.
"""

import copy
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from s2_helpers import (
    ContractError,
    app_base_url,
    assert_local_health_url,
    git_head_sha,
    health_url,
    read_run_doc_or_raise,
    startup_command,
    wait_for_health,
)
from s4_constants import (
    JUDGING_CRITERIA,
    RULE_P01,
    RULE_P02,
    RULE_P02A,
    RULE_P02B,
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


class AppProcess:
    """Controls the application process for black-box testing and captures stdout/stderr."""

    def __init__(self):
        self.proc = None
        self.stdout_file = None
        self.stderr_file = None
        self.stdout_path = None
        self.stderr_path = None

    def start(self):
        cmd = startup_command()
        expected_sha = git_head_sha()
        repo_root = Path(__file__).resolve().parents[2]

        # Use temporary files so pipes do not block on high buffer usage
        self.stdout_file = tempfile.NamedTemporaryFile(mode="w+", delete=False, encoding="utf-8")
        self.stderr_file = tempfile.NamedTemporaryFile(mode="w+", delete=False, encoding="utf-8")
        self.stdout_path = self.stdout_file.name
        self.stderr_path = self.stderr_file.name

        self.proc = subprocess.Popen(
            shlex.split(cmd),
            cwd=repo_root,
            stdout=self.stdout_file,
            stderr=self.stderr_file,
        )
        wait_for_health(expected_sha)
        return self

    def stop(self):
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None

        if self.stdout_file is not None and not self.stdout_file.closed:
            self.stdout_file.close()
        if self.stderr_file is not None and not self.stderr_file.closed:
            self.stderr_file.close()

    def get_stdout(self) -> str:
        """Returns captured stdout from the app process."""
        if self.stdout_path and os.path.isfile(self.stdout_path):
            with open(self.stdout_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        return ""

    def get_stderr(self) -> str:
        """Returns captured stderr from the app process."""
        if self.stderr_path and os.path.isfile(self.stderr_path):
            with open(self.stderr_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        return ""


class FakeVendorCleanupBoundary:
    """Test-owned fake vendor / local cleanup boundary that observes resource connection,

    tracks call counts, records failed DELETE attempts, and tests failure injection.
    """

    def __init__(self):
        self._created_resources = {}  # session_id -> resource_handle
        self._active_resources = set()  # set of resource_handles currently allocated
        self._delete_calls = []  # list of records: {"session_id": sid, "handle": h, "success": bool}
        self._inject_failure = False

    def reset(self):
        self._created_resources.clear()
        self._active_resources.clear()
        self._delete_calls.clear()
        self._inject_failure = False

    def set_inject_failure(self, inject: bool):
        self._inject_failure = inject

    def record_create(self, session_id: str, resource_handle: str):
        """Observes vendor resource allocation before cleanup can occur."""
        self._created_resources[session_id] = resource_handle
        self._active_resources.add(resource_handle)

    def delete(self, session_id: str, resource_handle: str | None = None) -> tuple[int, dict]:
        """Performs cleanup of vendor resource. Records failed attempts and handle retention."""
        handle = resource_handle or self._created_resources.get(session_id)
        if self._inject_failure:
            self._delete_calls.append({"session_id": session_id, "handle": handle, "success": False})
            # Resource handle is explicitly retained on upstream failure
            return 502, {"error": "upstream_cleanup_failure", "resource_retained": True, "handle": handle}

        # Successful attempt
        is_active = handle in self._active_resources if handle else False
        if is_active:
            self._active_resources.remove(handle)
            clean_count = 1
        else:
            clean_count = 0  # Idempotent repeat: zero additional resources torn down

        self._delete_calls.append({"session_id": session_id, "handle": handle, "success": True, "delta": clean_count})
        return 200, {
            "status": "cleaned",
            "session_id": session_id,
            "resource_handle": handle,
            "resources_torn_down": clean_count,
            "retained": False,
        }

    def create_call_count(self) -> int:
        return len(self._created_resources)

    def delete_call_count(self) -> int:
        """Returns total number of DELETE attempts made to this boundary."""
        return len(self._delete_calls)

    def successful_cleanup_count(self) -> int:
        return sum(1 for c in self._delete_calls if c["success"])

    def failed_delete_count(self) -> int:
        return sum(1 for c in self._delete_calls if not c["success"])

    def is_resource_active(self, handle: str) -> bool:
        return handle in self._active_resources

    def get_delete_records(self) -> list[dict]:
        return list(self._delete_calls)


# Global boundary instance for test observations
global_fake_boundary = FakeVendorCleanupBoundary()


def _s4_request(method: str, url: str, payload=None, timeout: float = 5.0) -> tuple[int, dict]:
    """Issues HTTP request to localhost server and safely decodes JSON or returns raw body dictionary."""
    assert_local_health_url(url)
    data = None
    headers = {"Connection": "close"}
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
    """Generates a normative, complete synthetic profile conforming to sah.persona.v1."""
    profile = {
        "schema_version": SCHEMA_VERSION_PERSONA,
        "profile_id": f"prof-{role}-{scenario}-v1",
        "scenario": scenario,
        "role": role,
        "display_name": "Synthetic Alex" if role == "body_double" else "Synthetic Dana",
        "avatar": {
            "kind": "synthetic",
            "asset_id": "avatar-synth-01" if role == "body_double" else "avatar-synth-02",
            "rendering": "2d_canvas",
        },
        "voice": {
            "kind": "synthetic",
            "voice_id": "synth-voice-en-01" if role == "body_double" else "synth-voice-en-02",
        },
        "personality": {
            "tone": "collaborative",
            "style": "assertive_direct" if role == "body_double" else "evaluative_probing",
            "pacing": "moderate",
        },
        "goals": [
            "establish_fair_terms",
            "explore_counterpart_constraints",
            "maintain_professional_relationship",
        ],
        "visible_knowledge": [
            "initial_offer_range",
            "project_scope",
            "standard_payment_terms",
        ],
        "negotiation_policy": {
            "strategy": "interest_based",
            "anchor_policy": "firm",
            "concession_rate": "measured",
        },
        "hidden_need_reveal_rules": {
            "trigger": "probe_budget_or_signon",
            "reveal_mode": "gradual",
            "revealed_flag": False,
        },
        "delegated_authority": {
            "level": authority_level,
            "max_concession_pct": 15,
            "can_finalize": False,
        },
        "prohibited_actions": [
            "real_person_impersonation",
            "financial_signing",
            "real_meeting",
            "biometric_collection",
            "voice_cloning",
        ],
        "escalation": {
            "on_prohibited_request": "refuse_and_redirect",
            "on_persistent_violation": "terminate_session",
        },
        "retention": {
            "media": "ephemeral",
            "transcript_allowed": True,
            "ttl_seconds": 3600,
        },
        "version": 1,
    }
    profile["profile_hash"] = compute_canonical_profile_hash(profile)
    return profile


def check_readme_sections(content: str) -> list[str]:
    """Checks that root README.md has all required substantive sections."""
    required = [
        ("overview", ["overview", "project overview", "introduction"]),
        ("architecture", ["architecture", "system architecture", "design"]),
        ("setup", ["setup", "installation", "quickstart", "getting started"]),
        ("verification", ["verification", "testing", "running tests"]),
        ("clean_checkout", ["clean checkout", "manifest", "file structure"]),
    ]
    missing = []
    lower = content.lower()
    for section_id, synonyms in required:
        if not any(s in lower for s in synonyms):
            missing.append(section_id)
    return missing


def analyze_demo_script(content: str) -> dict:
    """Analyzes demo script word count, cues, and bounded duration (<= 180s)."""
    words = re.findall(r"\b\w+\b", content)
    word_count = len(words)
    # Average speaking rate: 140 words per minute (2.33 words/second)
    est_duration = word_count / 2.33
    is_under_3_min = est_duration <= 180.0
    has_cues = any(c in content.lower() for c in ("[action", "[visual", "[cue", "demo:", "step 1", "speaker:"))
    return {
        "word_count": word_count,
        "est_duration_seconds": est_duration,
        "is_under_3_minutes": is_under_3_min,
        "has_cues": has_cues,
    }


def analyze_writeup(content: str) -> dict:
    """Analyzes hackathon writeup word count (strictly 100-500 words) and structure."""
    words = re.findall(r"\b\w+\b", content)
    word_count = len(words)
    is_valid_range = 100 <= word_count <= 500
    has_sections = any(s in content.lower() for s in ("problem", "solution", "architecture", "impact"))
    return {
        "word_count": word_count,
        "is_valid_range": is_valid_range,
        "has_substantive_content": has_sections,
    }


def check_real_mock_matrix(content: str) -> dict:
    """Checks that Real vs. Mock matrix explicitly covers Stages 1-4 with real/mock classifications."""
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


def check_judging_rubric(content: str) -> dict:
    """Checks that judging rubric self-check covers all five hackathon criteria."""
    lower = content.lower()
    missing = []
    for crit in JUDGING_CRITERIA:
        term = crit.replace("_", " ")
        if term not in lower and crit not in lower:
            missing.append(crit)
    return {
        "covered": len(missing) == 0,
        "missing": missing,
    }


def check_clean_checkout_manifest(content: str) -> dict:
    """Verifies that clean checkout manifest lists key repo components."""
    lower = content.lower()
    expected = ["app", "main.py", "factory-lite", "run.md", "protocol.md"]
    missing = [e for e in expected if e not in lower]
    return {
        "valid": len(missing) == 0,
        "missing": missing,
    }
