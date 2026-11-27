"""Stage 4A requirement 7: deterministic versioned fidelity report.

The report is a typed application-boundary artifact: versioned rubric, the
approved profile/instruction hashes, the disclosure record, non-compensable
authority/safety/disclosure terminal gates, hidden-need timing and
persona/policy stability across retry.
"""
import unittest

from s4_helpers import (
    POLICY_VERSION,
    RUBRIC_VERSION,
    S4App,
    SHA256_RE,
    fidelity,
    make_practice_session,
    post_json,
    require_ok,
    send_turn,
    standard_personas,
)


class TestDeterministicFidelityReport(unittest.TestCase):
    app = None

    @classmethod
    def setUpClass(cls):
        cls.app = S4App().start()

    @classmethod
    def tearDownClass(cls):
        if cls.app is not None:
            cls.app.stop()

    def _attempt_one_with_timed_reveal(self):
        personas = standard_personas()
        sid = make_practice_session(personas)
        status, first = send_turn(sid, "Thanks for the time; let's get oriented.", 1,
                                  f"{sid}-fid-1")
        self.assertEqual(status, 200, f"body={first}")
        self.assertIs(first["scenario"]["hidden_need_revealed"], False)
        status, second = send_turn(sid, "What is the budget you can work with?", 2,
                                   f"{sid}-fid-2")
        self.assertEqual(status, 200, f"body={second}")
        self.assertIs(second["scenario"]["hidden_need_revealed"], True)
        status, fb = post_json(f"/api/rehearsal/sessions/{sid}/feedback")
        self.assertEqual(status, 200, f"body={fb}")
        return sid, personas

    def test_report_has_versioned_rubric_and_required_hashes(self):
        sid, personas = self._attempt_one_with_timed_reveal()
        status, report = fidelity(sid)
        require_ok(status, report, "fidelity report")
        self.assertEqual(report.get("schema"), "sah.fidelity.v1")
        self.assertEqual(report.get("rubric_version"), RUBRIC_VERSION)
        self.assertRegex(report.get("report_hash", ""), SHA256_RE)
        self.assertRegex(report.get("scenario_hash", ""), SHA256_RE)
        self.assertEqual(
            (report.get("profile_hashes") or {}).get("body_double"),
            personas["body_double"]["profile_hash"],
        )
        self.assertEqual(
            (report.get("profile_hashes") or {}).get("counterpart"),
            personas["counterpart"]["profile_hash"],
        )
        for role in ("body_double", "counterpart"):
            self.assertRegex((report.get("instruction_hashes") or {}).get(role, ""), SHA256_RE)
        disclosure = report.get("disclosure") or {}
        self.assertIs(disclosure.get("present"), True)
        self.assertIs(disclosure.get("synthetic"), True)
        self.assertEqual(disclosure.get("id"), "sah_disclosure_v1")

    def test_authority_safety_and_disclosure_are_terminal_gates(self):
        sid, _ = self._attempt_one_with_timed_reveal()
        status, report = fidelity(sid)
        require_ok(status, report, "fidelity report")
        gates = report.get("gates") or {}
        self.assertEqual(gates.get("disclosure"), 4, f"gates={gates}")
        self.assertEqual(gates.get("authority"), 4, f"gates={gates}")
        self.assertEqual(gates.get("safety"), 4, f"gates={gates}")
        self.assertIs(report.get("gates_terminal"), True,
                      "gate dimensions are not marked terminal / non-compensable")

    def test_hidden_need_timing_reveals_on_first_qualifying_probe_only(self):
        sid, _ = self._attempt_one_with_timed_reveal()
        status, report = fidelity(sid)
        require_ok(status, report, "fidelity report")
        timing = report.get("hidden_need_timing") or {}
        self.assertIs(timing.get("revealed"), True)
        self.assertIs(timing.get("revealed_before_trigger"), False)
        self.assertIs(timing.get("revealed_on_first_qualifying_probe"), True)
        self.assertEqual(timing.get("revealed_at_turn"), 2,
                         f"reveal timing is wrong: {timing}")

    def test_report_is_deterministic_on_repeated_read(self):
        sid, _ = self._attempt_one_with_timed_reveal()
        status, first = fidelity(sid)
        require_ok(status, first, "first fidelity report")
        status, second = fidelity(sid)
        require_ok(status, second, "second fidelity report")
        self.assertEqual(second, first,
                         "fidelity report changed between two reads of the same attempt")

    def test_persona_and_policy_stay_stable_across_retry(self):
        sid, personas = self._attempt_one_with_timed_reveal()
        status, retry = post_json(f"/api/rehearsal/sessions/{sid}/retry")
        self.assertEqual(status, 200, f"body={retry}")
        for index, utterance in enumerate(
            ["Second attempt, different scope.", "What budget range applies?"], start=1
        ):
            status, body = send_turn(sid, utterance, index, f"{sid}-fid-a2-{index}")
            self.assertEqual(status, 200, f"body={body}")
        status, fb = post_json(f"/api/rehearsal/sessions/{sid}/feedback")
        self.assertEqual(status, 200, f"body={fb}")

        status, report = fidelity(sid)
        require_ok(status, report, "fidelity report after retry")
        self.assertIs(report.get("persona_stable_across_retry"), True)
        self.assertEqual(report.get("policy_version"), POLICY_VERSION)
        self.assertEqual(report["profile_hashes"]["counterpart"],
                         personas["counterpart"]["profile_hash"],
                         "persona changed across retry")
        timing = report.get("hidden_need_timing") or {}
        self.assertIs(timing.get("revealed_on_first_qualifying_probe"), True)
        self.assertEqual(timing.get("revealed_at_turn"), 2)


if __name__ == "__main__":
    unittest.main()
