"""Stage 4A requirement 2: two distinct roles and allowlisted projections.

One session carries two separately compiled personas (distinct approved
hashes, goals, visible knowledge and seeded hidden markers). Each of the three
consumers -- body double, counterpart, browser -- receives a direct
allowlisted projection. The test recursively proves that every unauthorized
key and every foreign marker is absent, and that each authorized internal
marker appears only in its own view.
"""
import unittest

from s4_helpers import (
    BD_MARKER,
    CP_MARKER,
    S4App,
    assert_no_key,
    assert_no_value,
    create_session,
    find_values,
    make_practice_session,
    projection,
    require_ok,
    standard_personas,
)

BODY_DOUBLE_ALLOWED_KEYS = {
    "schema", "view", "role", "attempt", "scenario_id", "profile_id",
    "profile_hash", "goals", "visible_knowledge", "personality", "authority",
    "disclosure", "hidden_state", "policy_version", "bounds",
}
COUNTERPART_ALLOWED_KEYS = BODY_DOUBLE_ALLOWED_KEYS

BROWSER_ALLOWED_KEYS = {
    "schema", "view", "role", "attempt", "scenario_id", "state",
    "visible_facts", "disclosure", "policy_version", "transcript_cursor",
    "bounds",
}
BROWSER_FORBIDDEN_KEYS = {
    "goals", "hidden_state", "hidden_needs", "profile_hash",
    "instruction_hash", "personality", "authority", "policy",
    "negotiation_policy", "retention", "consent", "provenance",
}

REQUIRED_INTERNAL_KEYS = {"goals", "visible_knowledge", "hidden_state",
                          "disclosure", "policy_version", "authority"}


class TestTwoRoleProjectionIsolation(unittest.TestCase):
    app = None

    @classmethod
    def setUpClass(cls):
        cls.app = S4App().start()

    @classmethod
    def tearDownClass(cls):
        if cls.app is not None:
            cls.app.stop()

    def _practice_session(self):
        personas = standard_personas()
        sid = make_practice_session(personas)
        return sid, personas

    def test_session_binds_both_distinct_personas_with_their_hashes(self):
        personas = standard_personas()
        status, created = create_session(personas)
        self.assertEqual(status, 201, f"body={created}")
        hashes = created.get("profile_hashes") or {}
        self.assertEqual(
            hashes.get("body_double"), personas["body_double"]["profile_hash"],
            "session did not bind the body-double approved profile hash",
        )
        self.assertEqual(
            hashes.get("counterpart"), personas["counterpart"]["profile_hash"],
            "session did not bind the counterpart approved profile hash",
        )
        self.assertNotEqual(hashes["body_double"], hashes["counterpart"])
        self.assertEqual(created.get("attempt"), 1)
        self.assertEqual(created.get("authority_tier"), "A2")

    def test_body_double_view_carries_its_own_marker_and_not_the_counterparts(self):
        sid, personas = self._practice_session()
        status, view = projection(sid, "body_double")
        require_ok(status, view, "body_double projection")
        self.assertEqual(view.get("view"), "body_double")
        self.assertEqual(view.get("profile_hash"), personas["body_double"]["profile_hash"])
        missing = REQUIRED_INTERNAL_KEYS - set(view)
        self.assertEqual(sorted(missing), [],
                         f"body-double projection omits required key(s): {sorted(missing)}")
        self.assertTrue(find_values(view, BD_MARKER),
                        "body double cannot see its own authorized internal marker")
        assert_no_value(self, view, [CP_MARKER],
                        "body_double projection")
        extra = set(view) - BODY_DOUBLE_ALLOWED_KEYS
        self.assertEqual(sorted(extra), [],
                         f"body-double projection exposes non-allowlisted key(s): {sorted(extra)}")

    def test_counterpart_view_carries_its_own_marker_and_not_the_body_doubles(self):
        sid, personas = self._practice_session()
        status, view = projection(sid, "counterpart")
        require_ok(status, view, "counterpart projection")
        self.assertEqual(view.get("view"), "counterpart")
        self.assertEqual(view.get("profile_hash"), personas["counterpart"]["profile_hash"])
        missing = REQUIRED_INTERNAL_KEYS - set(view)
        self.assertEqual(sorted(missing), [],
                         f"counterpart projection omits required key(s): {sorted(missing)}")
        self.assertTrue(find_values(view, CP_MARKER),
                        "counterpart cannot see its own authorized hidden marker")
        assert_no_value(self, view, [BD_MARKER], "counterpart projection")
        extra = set(view) - COUNTERPART_ALLOWED_KEYS
        self.assertEqual(sorted(extra), [],
                         f"counterpart projection exposes non-allowlisted key(s): {sorted(extra)}")

    def test_browser_view_has_only_public_state_and_no_internal_markers(self):
        sid, _ = self._practice_session()
        status, view = projection(sid, "browser")
        require_ok(status, view, "browser projection")
        self.assertEqual(view.get("view"), "browser")
        self.assertEqual(view.get("scenario_id"), "alex_dana")
        self.assertIn("disclosure", view, "browser view must carry the disclosure")
        self.assertTrue(view.get("visible_facts"), "browser view carries no visible facts")
        assert_no_value(self, view, [BD_MARKER, CP_MARKER], "browser projection")
        assert_no_key(self, view, BROWSER_FORBIDDEN_KEYS, "browser projection")
        extra = set(view) - BROWSER_ALLOWED_KEYS
        self.assertEqual(sorted(extra), [],
                         f"browser projection exposes non-allowlisted key(s): {sorted(extra)}")

    def test_three_views_are_mutually_distinct(self):
        sid, _ = self._practice_session()
        _, bd = projection(sid, "body_double")
        _, cp = projection(sid, "counterpart")
        _, br = projection(sid, "browser")
        self.assertNotEqual(bd, cp, "body-double and counterpart projections are identical")
        self.assertNotEqual(bd, br, "body-double and browser projections are identical")
        self.assertNotEqual(cp, br, "counterpart and browser projections are identical")
        self.assertNotEqual(bd.get("goals"), cp.get("goals"),
                            "the two roles share goals instead of distinct approved goals")
        self.assertNotEqual(bd.get("visible_knowledge"), cp.get("visible_knowledge"),
                            "the two roles share visible knowledge instead of distinct allowlists")

    def test_unknown_view_is_rejected_and_unknown_session_is_not_found(self):
        sid, _ = self._practice_session()
        status, body = projection(sid, "vendor")
        self.assertEqual(status, 400, f"body={body}")
        self.assertEqual(body.get("error"), "invalid_view")
        status, _ = projection("does-not-exist", "browser")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
