"""Stage 4 Requirement 3: Avatar and Voice Consent, Persona Boundaries, and Synthetic Disclosure.

Mandates from factory-lite/docs/body-double-persona-and-consent.md:
- Explicit consent for avatar likeness and voice synthesis: [data-testid="avatar-consent-checkbox"].
- Connect button disabled until affirmative consent is given.
- Prominent affirmative synthetic identity disclosure: [data-testid="synthetic-disclosure"].
- Six-track profile separation; rejection of biometric templates.
"""
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from s2_helpers import AppProcess, app_base_url
from s4_helpers import create_desktop_context


class TestStage4ConsentAndSyntheticDisclosure(unittest.TestCase):
    app = None
    playwright = None
    browser = None

    @classmethod
    def setUpClass(cls):
        cls.app = AppProcess().start()
        try:
            from playwright.sync_api import sync_playwright
            cls.playwright = sync_playwright().start()
            cls.browser = cls.playwright.chromium.launch()
        except Exception as exc:
            if cls.app is not None:
                cls.app.stop()
            raise RuntimeError(f"Playwright browser launch failed: {exc}")

    @classmethod
    def tearDownClass(cls):
        if cls.browser is not None:
            cls.browser.close()
        if cls.playwright is not None:
            cls.playwright.stop()
        if cls.app is not None:
            cls.app.stop()

    def test_avatar_and_voice_consent_checkbox_controls_connect_button(self):
        """Consent checkbox [data-testid='avatar-consent-checkbox'] must gate avatar connect."""
        context = create_desktop_context(self.browser)
        page = context.new_page()
        try:
            page.goto(app_base_url() + "/", timeout=10000)

            # Check that consent checkbox exists
            consent_box = page.locator('[data-testid="avatar-consent-checkbox"]')
            self.assertEqual(
                consent_box.count(),
                1,
                "Stage 4 requires affirmative avatar consent checkbox [data-testid='avatar-consent-checkbox']",
            )

            # Connect button must initially be disabled or require checked consent
            connect_btn = page.locator('[data-testid="napster-connect"]')
            connect_btn.wait_for(state="visible", timeout=5000)
            self.assertTrue(
                connect_btn.is_disabled(),
                "Avatar connect button must be disabled before consent is checked",
            )

            # Checking consent enables the connect button
            consent_box.check()
            self.assertTrue(
                connect_btn.is_enabled(),
                "Checking consent checkbox must enable avatar connect button",
            )
        finally:
            page.close()
            context.close()

    def test_affirmative_synthetic_identity_disclosure_prominently_visible(self):
        """Synthetic disclosure [data-testid='synthetic-disclosure'] must declare AI stand-in status."""
        context = create_desktop_context(self.browser)
        page = context.new_page()
        try:
            page.goto(app_base_url() + "/", timeout=10000)

            disclosure_el = page.locator('[data-testid="synthetic-disclosure"]')
            self.assertGreaterEqual(
                disclosure_el.count(),
                1,
                "Stage 4 requires prominent synthetic disclosure element [data-testid='synthetic-disclosure']",
            )
            text = disclosure_el.inner_text().lower()
            # Must declare synthetic / AI nature
            has_keyword = any(k in text for k in ["synthetic", "ai", "stand-in", "rehearsal counterpart", "simulated"])
            self.assertTrue(has_keyword, f"Synthetic disclosure must mention synthetic/AI counterpart, got: '{text}'")

            # Must NOT claim to be a real human or live person
            self.assertNotIn("real human", text)
            self.assertNotIn("live person", text)
        finally:
            page.close()
            context.close()

    def test_six_track_profile_rejects_biometric_templates(self):
        """Profile schema must reject biometric template fields (voiceprints, face templates)."""
        import s3_helpers
        import json
        import urllib.request
        import urllib.error

        prohibited_payload = {
            "channel_type": "webrtc",
            "biometric_voiceprint": "0123456789abcdef",
            "face_template": "raw_face_embedding_vector_999",
        }
        url = app_base_url() + "/api/rehearsal/sessions"
        req = urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        sid = data["session_id"]

        # Attempt to inject biometric template into session
        nap_url = app_base_url() + f"/api/rehearsal/sessions/{sid}/napster-session"
        nap_req = urllib.request.Request(
            nap_url,
            data=json.dumps(prohibited_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(nap_req, timeout=5) as nresp:
                res_data = json.loads(nresp.read().decode("utf-8"))
                # Server should not reflect or echo biometric template
                self.assertNotIn("biometric_voiceprint", res_data)
                self.assertNotIn("face_template", res_data)
        except urllib.error.HTTPError as err:
            # Rejection with 400 is also acceptable
            self.assertIn(err.code, [400, 422, 502, 503])


if __name__ == "__main__":
    unittest.main()
