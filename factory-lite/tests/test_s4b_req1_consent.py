"""Stage 4B requirement 1: granular consent, separate scopes and gates.

Direct black-box proof that the six consent scopes are recorded and observable
independently, that an absent scope blocks its operation with an exact typed
403, that consent never bundles, and that mid-session withdrawal takes effect.

Contract: ``factory-lite/docs/stage-4b-acceptance-contract.md`` sections 2-4.
"""
import json
import unittest

from s4b_helpers import (
    CONSENT_POLICY_VERSION,
    SCOPES,
    S4BApp,
    FakeVendor,
    assert_consent_required,
    consent_get,
    consent_set,
    grant,
    grant_many,
    make_practice_session,
    mic_start,
    napster_create,
    practice,
    require_session,
    research_export,
    session_hash,
    snapshot,
    transcript_save,
    transcript_saved,
    withdraw,
)


class TestGranularConsent(unittest.TestCase):
    app = None
    vendor = None

    @classmethod
    def setUpClass(cls):
        cls.vendor = FakeVendor()
        cls.vendor.__enter__()
        cls.app = S4BApp(env=cls.vendor.env(), capture_logs=False).start()

    @classmethod
    def tearDownClass(cls):
        if cls.app is not None:
            cls.app.stop()
        if cls.vendor is not None:
            cls.vendor.__exit__(None, None, None)

    def setUp(self):
        self.vendor.reset()

    # -- record shape ------------------------------------------------------

    def test_six_scopes_are_separately_visible_and_denied_by_default(self):
        sid = require_session()
        status, body = consent_get(sid)
        self.assertEqual(status, 200, f"consent read failed: status={status} body={body}")
        self.assertEqual(body.get("schema"), "sah.consent.v1")
        self.assertEqual(body.get("policy_version"), CONSENT_POLICY_VERSION)
        self.assertRegex(body.get("session_hash", ""), r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(body.get("session_hash"), session_hash(sid),
                         "consent record is not bound to the session by canonical hash")
        scopes = body.get("scopes") or {}
        self.assertEqual(sorted(scopes), sorted(SCOPES),
                         f"consent record does not expose exactly the six scopes: {sorted(scopes)}")
        for scope in SCOPES:
            entry = scopes[scope]
            self.assertIs(entry.get("granted"), False,
                          f"scope {scope!r} is not denied by default: {entry}")
            expected_applicable = scope != "subject_consent"
            self.assertIs(entry.get("applicable"), expected_applicable,
                          f"scope {scope!r} has wrong applicability: {entry}")

    def test_granting_one_scope_does_not_bundle_others(self):
        sid = require_session()
        status, body = consent_set(sid, "avatar", True)
        self.assertEqual(status, 200, f"avatar grant failed: status={status} body={body}")
        self.assertEqual(body.get("scope"), "avatar")
        self.assertIs(body.get("granted"), True)
        self.assertEqual(body.get("session_hash"), session_hash(sid))
        self.assertRegex(body.get("recorded_at_utc", ""), r"^\d{4}-\d{2}-\d{2}T")

        status, record = consent_get(sid)
        self.assertEqual(status, 200, f"body={record}")
        scopes = record["scopes"]
        self.assertIs(scopes["avatar"]["granted"], True)
        for scope in ("rehearsal", "mic", "transcript_save", "research", "subject_consent"):
            self.assertIs(scopes[scope]["granted"], False,
                          f"granting avatar bundled {scope!r}")

    def test_unknown_scope_is_rejected(self):
        sid = require_session()
        status, body = consent_set(sid, "telepathy", True)
        self.assertEqual(status, 400, f"body={body}")
        self.assertEqual(body.get("error"), "invalid_scope")
        status, record = consent_get(sid)
        self.assertEqual(status, 200, f"body={record}")
        for scope in SCOPES:
            self.assertIs(record["scopes"][scope]["granted"], False,
                          f"rejected scope changed {scope!r}")

    def test_subject_consent_is_not_applicable_in_v1(self):
        sid = require_session()
        status, body = consent_set(sid, "subject_consent", True)
        self.assertEqual(status, 409, f"body={body}")
        self.assertEqual(body.get("error"), "subject_consent_not_applicable")
        status, record = consent_get(sid)
        self.assertEqual(status, 200, f"body={record}")
        entry = record["scopes"]["subject_consent"]
        self.assertIs(entry.get("applicable"), False)
        self.assertIs(entry.get("granted"), False)

    def test_non_boolean_grant_is_rejected(self):
        sid = require_session()
        for value in ("yes", 1, None):
            status, body = consent_set(sid, "rehearsal", value)
            self.assertEqual(status, 400,
                             f"granted={value!r} was not rejected: status={status} body={body}")
            self.assertEqual(body.get("error"), "invalid_consent")

    # -- gates -------------------------------------------------------------

    def test_vendor_create_requires_rehearsal_consent(self):
        sid = make_practice_session()
        assert_consent_required(self, napster_create(sid), "rehearsal",
                                "vendor create without rehearsal consent")
        self.assertEqual(self.vendor.ledger()["created_count"], 0,
                         "vendor was contacted before rehearsal consent was granted")

    def test_vendor_create_requires_avatar_consent_after_rehearsal(self):
        sid = make_practice_session()
        grant(sid, "rehearsal")
        assert_consent_required(self, napster_create(sid), "avatar",
                                "vendor create without avatar consent")
        self.assertEqual(self.vendor.ledger()["created_count"], 0,
                         "vendor was contacted without avatar consent")

    def test_microphone_requires_mic_consent(self):
        sid = make_practice_session()
        assert_consent_required(self, mic_start(sid), "mic", "mic start without consent")
        grant(sid, "mic")
        status, body = mic_start(sid)
        self.assertEqual(status, 200, f"body={body}")
        self.assertEqual(body.get("status"), "started")
        self.assertIs(body.get("synthetic"), True)

    def test_transcript_save_requires_consent_and_is_retrievable(self):
        sid = make_practice_session()
        assert_consent_required(self, transcript_save(sid), "transcript_save",
                                "transcript save without consent")
        status, body = transcript_saved(sid)
        self.assertEqual(status, 404, f"a transcript exists without consent: status={status} body={body}")

        grant(sid, "transcript_save")
        utterance = "Let us discuss the budget and the terms."
        status, body = practice(sid, utterance)
        self.assertEqual(status, 200, f"practice failed: status={status} body={body}")
        status, body = transcript_save(sid)
        self.assertEqual(status, 200, f"body={body}")
        self.assertIs(body.get("saved"), True)
        self.assertEqual(body.get("retention_hours"), 24)

        status, saved = transcript_saved(sid)
        self.assertEqual(status, 200, f"body={saved}")
        utterances = [t.get("utterance") for t in saved.get("transcript", [])]
        self.assertIn(utterance, utterances, "saved transcript lost the user utterance")

    def test_research_export_requires_consent_and_is_deidentified(self):
        sid = make_practice_session()
        assert_consent_required(self, research_export(sid), "research",
                                "research export without consent")

        grant(sid, "research")
        utterance = "My budget is tight and my terms are firm."
        status, body = practice(sid, utterance)
        self.assertEqual(status, 200, f"practice failed: status={status} body={body}")
        status, export = research_export(sid)
        self.assertEqual(status, 200, f"body={export}")
        self.assertIs(export.get("exported"), True)
        self.assertIs(export.get("deidentified"), True)
        aggregate = export.get("aggregate") or {}
        self.assertIsInstance(aggregate.get("turns"), int)
        self.assertNotIn(utterance, json.dumps(export, ensure_ascii=False),
                         "research export leaked the raw user utterance")

    # -- withdrawal --------------------------------------------------------

    def test_avatar_withdrawal_tears_down_vendor_and_keeps_text_practice(self):
        sid = make_practice_session()
        grant_many(sid, ("rehearsal", "avatar"))
        status, created = napster_create(sid)
        self.assertEqual(status, 200, f"body={created}")
        connection_id = created.get("connection_id")
        self.assertTrue(connection_id)
        self.assertEqual(self.vendor.ledger()["created_count"], 1)

        status, body = withdraw(sid, "avatar")
        self.assertEqual(status, 200, f"withdrawal failed: status={status} body={body}")
        ledger = self.vendor.ledger()
        self.assertEqual(len(ledger["deleted"]), 1,
                         f"avatar withdrawal did not tear down the vendor exactly once: {ledger}")
        self.assertIn(connection_id, ledger["deleted"][-1],
                      "avatar withdrawal deleted the wrong vendor connection")

        assert_consent_required(self, napster_create(sid), "avatar",
                                "vendor create after avatar withdrawal")
        status, body = practice(sid, "Text practice still works after avatar withdrawal.")
        self.assertEqual(status, 200, f"text practice blocked after avatar withdrawal: {body}")

    def test_transcript_withdrawal_deletes_saved_copy(self):
        sid = make_practice_session()
        grant(sid, "transcript_save")
        status, body = practice(sid, "A saved line about the budget.")
        self.assertEqual(status, 200, f"body={body}")
        status, body = transcript_save(sid)
        self.assertEqual(status, 200, f"body={body}")
        status, _ = transcript_saved(sid)
        self.assertEqual(status, 200)

        status, body = withdraw(sid, "transcript_save")
        self.assertEqual(status, 200, f"withdrawal failed: status={status} body={body}")
        status, body = transcript_saved(sid)
        self.assertEqual(status, 404,
                         f"saved transcript survived transcript_save withdrawal: status={status} body={body}")

    def test_rehearsal_withdrawal_ends_session(self):
        sid = make_practice_session()
        grant(sid, "rehearsal")
        status, body = practice(sid, "Opening line before withdrawal.")
        self.assertEqual(status, 200, f"body={body}")

        status, body = withdraw(sid, "rehearsal")
        self.assertEqual(status, 200, f"withdrawal failed: status={status} body={body}")
        status, snap = snapshot(sid)
        self.assertEqual(status, 200, f"body={snap}")
        self.assertEqual(snap.get("state"), "ended",
                         "withdrawing rehearsal did not end the session")
        status, body = practice(sid, "Should be rejected after withdrawal.")
        self.assertEqual(status, 409, f"practice still allowed after withdrawal: status={status} body={body}")
        self.assertEqual(body.get("error"), "invalid_state")

    def test_unknown_session_is_not_found(self):
        status, body = consent_get("does-not-exist")
        self.assertEqual(status, 404, f"body={body}")
        self.assertEqual(body.get("error"), "not_found")
        status, body = consent_set("does-not-exist", "avatar", True)
        self.assertEqual(status, 404, f"body={body}")


if __name__ == "__main__":
    unittest.main()
