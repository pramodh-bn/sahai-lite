"""Stage 5 acceptance contract (Verifier-authored, for Lead review).

Task: LITE-S5-CONTRACT-01. Base: ``6483ae9`` (dev-v3 head after Stage 4C
certification). This file is a *deliberately red* contract: every test below
asserts observable Stage 5 behaviour that does not exist at the base SHA, so
the whole module fails before implementation and must pass after it. No
application code, helper, docs or spec file is part of this change -- only this
new test module.

Run with::

    python -m pytest factory-lite/tests/test_stage5_contract.py -v

The module is also safe for the cumulative ``unittest discover`` harness: it
exposes ordinary ``unittest.TestCase`` classes and imports nothing that is
unavailable to the existing suite.

Conventions fixed by this contract (flag in review before dispatching the
Builder; changing them after implementation needs separate rationale per
``factory-lite/PROTOCOL.md``):

1. **Two avatars.** ``POST /api/rehearsal/sessions/<id>/napster-session``
   accepts an optional ``{"avatar": "dana"|"alex"}`` selector (default
   ``"dana"``). With ``NAPSTER_AGENT_ID`` and ``NAPSTER_ALEX_AGENT_ID`` both
   configured, the two selectors allocate independent connections scoped to
   the respective configured agent id. A second allocation for an avatar that
   is already connected returns ``409`` even while the other avatar is free.
   Existing Stage 3 body fields (``channel_type``, ``simulate_error``) keep
   working for ``dana``.
2. **Webcam token.** ``POST /api/rehearsal/sessions/<id>/webcam-token`` with
   body ``{"camera": "granted"|"denied", "microphone": "granted"|"denied"}``
   returns ``200`` with ``{"camera": <echoed status>, "text_practice_available":
   true}`` plus an optional ``token`` when the camera is granted. Deprivation
   is a normal, non-error outcome: text practice must remain usable. Unknown
   session ids return ``404``.
3. **Three-column practice UI.** Reaching practice through the existing
   ``/`` journey (start demo -> take my seat) shows three distinct panels at
   the same time: ``[data-testid="dana-avatar"]``,
   ``[data-testid="user-webcam"]`` and ``[data-testid="alex-avatar"]``. On a
   desktop viewport they are laid out side by side in that left-to-right order
   with non-overlapping boxes; on a 375x667 viewport all three remain visible
   and the document must not scroll horizontally.
4. **Coach whisper.** ``POST /api/rehearsal/sessions/<id>/coach-whisper``
   accepts ``{"utterance": str, "accepted": bool}`` (both optional;
   ``utterance`` defaults to the most recent practice turn), fires
   synchronously against the console coach, and returns ``200`` with
   ``{"suggestion": non-empty str, "context": non-empty str}``. The coach is
   read from ``FIREWORKS_API_KEY`` at request time and calls the Fireworks AI
   chat-completions endpoint
   ``https://api.fireworks.ai/inference/v1/chat/completions`` with an
   ``Authorization: Bearer <key>`` header; ``FIREWORKS_BASE_URL`` overrides the
   origin (default ``https://api.fireworks.ai``) so tests can use a loopback
   fake. The upstream call carries the latest user turn. Unknown session ids
   return ``404``; when no key is configured the route returns ``503`` with
   ``error == "coach_not_configured"`` and makes **no** upstream call.
5. **Coach summary.** ``GET /api/rehearsal/sessions/<id>/coach-summary``
   available once the attempt has reached evidence feedback ("session end")
   returns ``200`` with ``{"turns_shown": int, "turns_accepted": int,
   "corrections": list}`` for the current attempt. ``turns_shown`` counts the
   practice turns evaluated by the coach; ``turns_accepted`` counts whispers
   that marked the previous suggestion accepted; ``corrections`` is a list of
   ``{"turn": int, "note": str}`` objects (possibly empty). Unknown session
   ids return ``404``.

No live or paid calls: every test starts the local app on the documented
localhost URL and points vendor/LLM configuration at loopback fakes on
ephemeral ports. No credential is real and no external host is contacted.
"""
import json
import os
import re
import shlex
import subprocess
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from s2_helpers import (  # noqa: E402
    git_head_sha,
    get_json,
    post_json,
    startup_command,
    wait_for_health,
)
from s4c_helpers import (  # noqa: E402
    bounding_box,
    goto_home,
    is_visible,
    new_context,
    scroll_widths,
    start_app,
    to_practice,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

DANA_AGENT = "stage5-dana-agent"
ALEX_AGENT = "stage5-alex-agent"
FIREWORKS_KEY = "stage5-fake-fireworks-key"
FIREWORKS_PATH = "/inference/v1/chat/completions"
COACH_TEXT = "Ask for the total budget range, then probe sign-on flexibility."

# Keys the contract owns: stripped from the inherited environment and then set
# explicitly per test class so ambient developer configuration cannot leak in.
CONTRACT_ENV_KEYS = (
    "NAPSTER_BASE_URL",
    "NAPSTER_API_KEY",
    "NAPSTER_AGENT_ID",
    "NAPSTER_ALEX_AGENT_ID",
    "FIREWORKS_API_KEY",
    "FIREWORKS_BASE_URL",
)


# ---------------------------------------------------------------------------
# Loopback fakes
# ---------------------------------------------------------------------------

class _FakeHandler(BaseHTTPRequestHandler):
    recorder = None
    responder = None

    def _handle(self, method):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        record = {
            "method": method,
            "path": self.path,
            "headers": {k.lower(): v for k, v in self.headers.items()},
            "body": raw.decode("utf-8", errors="replace"),
        }
        self.recorder.append(record)
        status, payload = self.responder(record)
        data = b"" if payload is None else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        if data:
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if data:
            self.wfile.write(data)

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_DELETE(self):
        self._handle("DELETE")

    def log_message(self, *args):  # keep test output clean
        pass


def _start_fake(responder):
    """Start a loopback HTTP fake and return (server, recorded_requests, base_url)."""
    recorder = []

    class Handler(_FakeHandler):
        pass

    Handler.recorder = recorder
    Handler.responder = staticmethod(responder)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:%d" % server.server_address[1]
    return server, recorder, base


def _stop_fake(server):
    server.shutdown()
    server.server_close()


def _napster_responder(requests):
    counter = {"n": 0}

    def responder(record):
        if record["method"] == "POST":
            match = re.search(r"/public/agents/([^/]+)/connections", record["path"])
            agent = match.group(1) if match else ""
            counter["n"] += 1
            n = counter["n"]
            return 200, {
                "token": "fake-token-%s-%d" % (agent, n),
                "connection": {"id": "fake-connection-%d" % n},
            }
        if record["method"] == "DELETE":
            return 204, None
        return 404, {"error": "not_found"}

    return responder


def _fireworks_responder(record):
    if record["method"] == "POST":
        return 200, {
            "id": "chatcmpl-stage5-fake",
            "object": "chat.completion",
            "model": "accounts/fireworks/models/fake-coach",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": COACH_TEXT},
                    "finish_reason": "stop",
                }
            ],
        }
    return 404, {"error": "not_found"}


def _app_env(overrides):
    env = os.environ.copy()
    for name in CONTRACT_ENV_KEYS:
        env.pop(name, None)
    env.update({key: str(value) for key, value in overrides.items()})
    return env


def _start_contract_app(overrides):
    """Start the documented app with an isolated, explicit environment."""
    proc = subprocess.Popen(
        shlex.split(startup_command()), cwd=str(REPO_ROOT), env=_app_env(overrides)
    )
    try:
        wait_for_health(git_head_sha(), timeout_s=30)
    except Exception:
        proc.terminate()
        raise
    return proc


def _stop_contract_app(proc):
    if proc is None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


# ---------------------------------------------------------------------------
# Small API helpers (all localhost, via the certified helper base URL)
# ---------------------------------------------------------------------------

def _create_session():
    status, body = post_json("/api/rehearsal/sessions", {})
    assert status == 201, "session creation failed: %r %r" % (status, body)
    return body["session_id"]


def _to_practice(session_id):
    first, body = post_json(
        "/api/rehearsal/sessions/%s/advance" % session_id, {"to": "take_my_seat"}
    )
    assert first == 200, "demo->take_my_seat failed: %r %r" % (first, body)
    second, body = post_json(
        "/api/rehearsal/sessions/%s/advance" % session_id, {"to": "practice"}
    )
    assert second == 200, "take_my_seat->practice failed: %r %r" % (second, body)


def _practice(session_id, utterance):
    status, body = post_json(
        "/api/rehearsal/sessions/%s/practice" % session_id, {"utterance": utterance}
    )
    assert status == 200, "practice turn failed: %r %r" % (status, body)
    return body


# ---------------------------------------------------------------------------
# Requirement 1 and 2: two avatars, webcam permission
# ---------------------------------------------------------------------------

class TestStage5TwoAvatarsAndWebcam(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake, cls.requests, napster_base = _start_fake(_napster_responder([]))
        cls.app = _start_contract_app({
            "NAPSTER_BASE_URL": napster_base,
            "NAPSTER_API_KEY": "stage5-fake-napster-key",
            "NAPSTER_AGENT_ID": DANA_AGENT,
            "NAPSTER_ALEX_AGENT_ID": ALEX_AGENT,
        })

    @classmethod
    def tearDownClass(cls):
        _stop_contract_app(cls.app)
        _stop_fake(cls.fake)

    def test_dana_and_alex_allocate_independent_companion_sessions(self):
        session_id = _create_session()
        dana_status, dana = post_json(
            "/api/rehearsal/sessions/%s/napster-session" % session_id,
            {"channel_type": "webrtc", "avatar": "dana"},
        )
        alex_status, alex = post_json(
            "/api/rehearsal/sessions/%s/napster-session" % session_id,
            {"channel_type": "webrtc", "avatar": "alex"},
        )
        self.assertEqual(dana_status, 200, "dana avatar did not allocate: %r" % (dana,))
        self.assertEqual(alex_status, 200, "alex avatar did not allocate: %r" % (alex,))
        self.assertEqual(dana.get("status"), "ready")
        self.assertEqual(alex.get("status"), "ready")
        self.assertTrue(dana.get("token"), "dana allocation returned no token")
        self.assertTrue(alex.get("token"), "alex allocation returned no token")
        self.assertNotEqual(
            dana.get("connection_id"),
            alex.get("connection_id"),
            "both avatars returned the same connection id; sessions are not independent",
        )

    def test_both_configured_agents_are_used_upstream(self):
        session_id = _create_session()
        post_json(
            "/api/rehearsal/sessions/%s/napster-session" % session_id,
            {"avatar": "dana"},
        )
        post_json(
            "/api/rehearsal/sessions/%s/napster-session" % session_id,
            {"avatar": "alex"},
        )
        agents = [
            match.group(1)
            for record in self.requests
            for match in [re.search(r"/public/agents/([^/]+)/connections", record["path"])]
            if match is not None
        ]
        self.assertEqual(
            set(agents),
            {DANA_AGENT, ALEX_AGENT},
            "expected one upstream allocation per configured agent "
            "(NAPSTER_AGENT_ID=%r, NAPSTER_ALEX_AGENT_ID=%r); saw %r"
            % (DANA_AGENT, ALEX_AGENT, agents),
        )

    def test_second_allocation_for_same_avatar_is_rejected(self):
        session_id = _create_session()
        first, body = post_json(
            "/api/rehearsal/sessions/%s/napster-session" % session_id,
            {"avatar": "dana"},
        )
        self.assertEqual(first, 200, "first dana allocation failed: %r %r" % (first, body))
        second, body = post_json(
            "/api/rehearsal/sessions/%s/napster-session" % session_id,
            {"avatar": "dana"},
        )
        self.assertEqual(
            second, 409, "duplicate dana allocation must conflict, got %r %r" % (second, body)
        )

    def test_webcam_token_granted_returns_permission_and_token(self):
        session_id = _create_session()
        status, body = post_json(
            "/api/rehearsal/sessions/%s/webcam-token" % session_id,
            {"camera": "granted", "microphone": "granted"},
        )
        self.assertEqual(status, 200, "granted webcam token failed: %r %r" % (status, body))
        self.assertEqual(body.get("camera"), "granted")
        self.assertTrue(body.get("token"), "granted camera must return a token")
        self.assertIs(body.get("text_practice_available"), True)

    def test_camera_and_mic_denial_is_graceful_and_text_practice_survives(self):
        session_id = _create_session()
        _to_practice(session_id)
        status, body = post_json(
            "/api/rehearsal/sessions/%s/webcam-token" % session_id,
            {"camera": "denied", "microphone": "denied"},
        )
        self.assertEqual(status, 200, "denial must be a normal outcome: %r %r" % (status, body))
        self.assertEqual(body.get("camera"), "denied")
        self.assertIs(body.get("text_practice_available"), True)
        reply = _practice(session_id, "What budget range is workable for you?")
        self.assertTrue(
            isinstance(reply.get("counterpart_reply"), str) and reply["counterpart_reply"],
            "text practice must keep working after camera/mic denial: %r" % (reply,),
        )

    def test_webcam_token_for_unknown_session_is_404(self):
        status, _ = post_json(
            "/api/rehearsal/sessions/does-not-exist/webcam-token", {"camera": "granted"}
        )
        self.assertEqual(status, 404)


# ---------------------------------------------------------------------------
# Requirement 3: three-column practice UI
# ---------------------------------------------------------------------------

class TestStage5ThreeColumnPracticeUI(unittest.TestCase):
    PANELS = ("dana-avatar", "user-webcam", "alex-avatar")

    @classmethod
    def setUpClass(cls):
        cls.app = start_app()
        from playwright.sync_api import sync_playwright

        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        if cls.browser is not None:
            cls.browser.close()
        if cls.playwright is not None:
            cls.playwright.stop()
        if cls.app is not None:
            cls.app.stop()

    def setUp(self):
        self.context = None
        self.page = None

    def tearDown(self):
        if self.page is not None:
            self.page.close()
        if self.context is not None:
            self.context.close()

    def _open_practice(self, viewport):
        self.context = new_context(self.browser, viewport)
        self.page = self.context.new_page()
        goto_home(self.page)
        to_practice(self.page)

    def test_three_panels_are_visible_simultaneously_on_desktop(self):
        self._open_practice("desktop")
        boxes = {}
        for panel in self.PANELS:
            selector = '[data-testid="%s"]' % panel
            self.assertTrue(
                is_visible(self.page, selector),
                "practice UI is missing a visible %s panel" % panel,
            )
            box = bounding_box(self.page, selector)
            self.assertIsNotNone(box, "%s has no layout box" % panel)
            self.assertGreater(box["width"], 0, "%s has zero width" % panel)
            self.assertGreater(box["height"], 0, "%s has zero height" % panel)
            boxes[panel] = box
        ordered = [boxes[name] for name in self.PANELS]
        self.assertLess(
            ordered[0]["x"], ordered[1]["x"],
            "dana avatar must be left of the user webcam: %r" % (boxes,),
        )
        self.assertLess(
            ordered[1]["x"], ordered[2]["x"],
            "user webcam must be left of the alex body double: %r" % (boxes,),
        )
        for left, right in zip(ordered, ordered[1:]):
            self.assertLessEqual(
                left["x"] + left["width"],
                right["x"] + 1,
                "panels overlap instead of forming three columns: %r" % (boxes,),
            )

    def test_three_panels_remain_visible_on_mobile_without_horizontal_scroll(self):
        self._open_practice("mobile")
        for panel in self.PANELS:
            self.assertTrue(
                is_visible(self.page, '[data-testid="%s"]' % panel),
                "mobile practice UI is missing a visible %s panel" % panel,
            )
        widths = scroll_widths(self.page)
        self.assertLessEqual(
            widths["html"], widths["inner"] + 1,
            "mobile practice scrolls horizontally: %r" % (widths,),
        )
        self.assertLessEqual(
            widths["body"], widths["inner"] + 1,
            "mobile body overflows horizontally: %r" % (widths,),
        )


# ---------------------------------------------------------------------------
# Requirement 4 and 5: coach whisper and summary
# ---------------------------------------------------------------------------

class TestStage5Coach(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake, cls.requests, fireworks_base = _start_fake(_fireworks_responder)
        cls.app = _start_contract_app({
            "FIREWORKS_API_KEY": FIREWORKS_KEY,
            "FIREWORKS_BASE_URL": fireworks_base,
        })

    @classmethod
    def tearDownClass(cls):
        _stop_contract_app(cls.app)
        _stop_fake(cls.fake)

    def _practice_session(self):
        session_id = _create_session()
        _to_practice(session_id)
        return session_id

    def test_whisper_returns_suggestion_and_context_synchronously(self):
        session_id = self._practice_session()
        _practice(session_id, "What budget range works for Dana?")
        status, body = post_json(
            "/api/rehearsal/sessions/%s/coach-whisper" % session_id,
            {"utterance": "What budget range works for Dana?", "accepted": False},
        )
        self.assertEqual(status, 200, "coach whisper failed: %r %r" % (status, body))
        self.assertIsInstance(body.get("suggestion"), str)
        self.assertTrue(body["suggestion"].strip(), "suggestion must be non-empty")
        self.assertIsInstance(body.get("context"), str)
        self.assertTrue(body["context"].strip(), "context must be non-empty")

    def test_whisper_uses_configured_key_and_latest_turn_upstream(self):
        session_id = self._practice_session()
        utterance = "Could you be flexible on sign-on?"
        _practice(session_id, utterance)
        status, body = post_json(
            "/api/rehearsal/sessions/%s/coach-whisper" % session_id,
            {"utterance": utterance},
        )
        self.assertEqual(status, 200, "coach whisper failed: %r %r" % (status, body))
        self.assertTrue(self.requests, "no upstream coach call was made")
        upstream = self.requests[-1]
        self.assertIn(
            FIREWORKS_PATH,
            upstream["path"],
            "coach did not call the Fireworks chat-completions endpoint: %r"
            % (upstream["path"],),
        )
        self.assertEqual(
            upstream["headers"].get("authorization"),
            "Bearer " + FIREWORKS_KEY,
            "coach call did not send 'Authorization: Bearer <FIREWORKS_API_KEY>'",
        )
        self.assertIn(
            utterance,
            upstream["body"],
            "coach call did not carry the latest user turn: %r" % (upstream["body"],),
        )

    def test_whisper_for_unknown_session_is_404(self):
        status, _ = post_json(
            "/api/rehearsal/sessions/does-not-exist/coach-whisper", {"utterance": "hi"}
        )
        self.assertEqual(status, 404)

    def test_summary_counts_turns_and_accepted_suggestions(self):
        session_id = self._practice_session()
        _practice(session_id, "What budget range works for Dana?")
        first, body = post_json(
            "/api/rehearsal/sessions/%s/coach-whisper" % session_id,
            {"utterance": "What budget range works for Dana?", "accepted": False},
        )
        self.assertEqual(first, 200, "first whisper failed: %r %r" % (first, body))
        _practice(session_id, "Would flexible sign-on help close this?")
        second, body = post_json(
            "/api/rehearsal/sessions/%s/coach-whisper" % session_id,
            {"utterance": "Would flexible sign-on help close this?", "accepted": True},
        )
        self.assertEqual(second, 200, "second whisper failed: %r %r" % (second, body))
        feedback, body = post_json("/api/rehearsal/sessions/%s/feedback" % session_id, {})
        self.assertEqual(feedback, 200, "feedback (session end anchor) failed: %r %r" % (feedback, body))
        status, summary = get_json("/api/rehearsal/sessions/%s/coach-summary" % session_id)
        self.assertEqual(status, 200, "coach summary failed: %r %r" % (status, summary))
        self.assertEqual(summary.get("turns_shown"), 2, "expected two coached turns: %r" % (summary,))
        self.assertEqual(summary.get("turns_accepted"), 1, "expected one accepted suggestion: %r" % (summary,))
        self.assertIsInstance(summary.get("corrections"), list, "corrections must be a list")
        for correction in summary["corrections"]:
            self.assertIsInstance(correction, dict)
            self.assertIn("turn", correction)
            self.assertIn("note", correction)

    def test_summary_for_unknown_session_is_404(self):
        status, _ = get_json("/api/rehearsal/sessions/does-not-exist/coach-summary")
        self.assertEqual(status, 404)


# ---------------------------------------------------------------------------
# Honest unconfigured coach: no key, no call, typed refusal
# ---------------------------------------------------------------------------

class TestStage5CoachUnconfigured(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake, cls.requests, fireworks_base = _start_fake(_fireworks_responder)
        # FIREWORKS_API_KEY deliberately absent; base URL still points at the
        # loopback fake so any accidental upstream call is observable.
        cls.app = _start_contract_app({"FIREWORKS_BASE_URL": fireworks_base})

    @classmethod
    def tearDownClass(cls):
        _stop_contract_app(cls.app)
        _stop_fake(cls.fake)

    def test_missing_key_returns_typed_unavailable_without_upstream_call(self):
        session_id = _create_session()
        _to_practice(session_id)
        _practice(session_id, "What budget range works for Dana?")
        status, body = post_json(
            "/api/rehearsal/sessions/%s/coach-whisper" % session_id, {"utterance": "hi"}
        )
        self.assertEqual(
            status, 503, "unconfigured coach must be a typed 503, got %r %r" % (status, body)
        )
        self.assertEqual(body.get("error"), "coach_not_configured")
        self.assertEqual(
            self.requests, [], "coach made an upstream call without FIREWORKS_API_KEY"
        )


if __name__ == "__main__":
    unittest.main()
