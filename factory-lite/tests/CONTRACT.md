# Stage 1 acceptance contract (Verifier-authored, for Lead review)

Translates `factory-lite/spec/stage-1.md` into the executable, black-box
tests in this directory. Run with:

```
py -3.12 -m unittest discover -s factory-lite/tests -p "test_*.py" -v
```

No application code is included here. The spec does not pin exact file
locations or wire formats, so this contract fixes the following conventions
for Builder to implement against. Flag any of these in review before
dispatching the Builder assignment; changing them after implementation
starts requires separate rationale per `factory-lite/PROTOCOL.md`.

| Req | Spec text | Convention fixed by this contract | Test file |
|---|---|---|---|
| 1 | one documented local startup command | `app/RUN.md` has a `## Run` heading with exactly one fenced command line | `test_req1_startup_command.py` |
| 2 | health/version reports actual build SHA | `app/RUN.md` also has a `## Health` heading whose fenced block's first line is the full health URL (e.g. `http://127.0.0.1:8000/health`); the hostname must be `localhost`, `127.0.0.1`, or `::1` (enforced before anything is launched/polled -- no external calls are possible even if the doc names an external host); that endpoint returns HTTP 200 JSON `{"status": "ok", "version": "<git HEAD sha>"}` | `test_req2_health_version.py` |
| 3 | container non-root | `app/Dockerfile` builds, and `docker run <image> id -u` reports a non-zero UID | `test_req3_container_nonroot.py` |
| 4 | dependency lock | `app/` contains a non-empty recognized lock file (`requirements.lock`, `poetry.lock`, `Pipfile.lock`, `uv.lock`, `package-lock.json`, `pnpm-lock.yaml`, or `yarn.lock`) | `test_req4_dependency_lock.py` |
| 5 | no secrets in repo | no git-tracked file matches common secret patterns (private keys, AWS/OpenAI/Stripe-style keys, `secret=`/`password=`/`api_key=` literals); no tracked `.env`-like file outside `.env.example`/`.env.sample`/`.env.template` | `test_req5_no_secrets.py` |
| 6 | independent harness exits nonzero for broken service, zero for healthy | `factory-lite/tests/harness/health_check.py` is a dependency-free CLI harness; proven against fixtures (healthy / 500 / unavailable / SHA-mismatch) under this test's own control | `test_req6_harness_contract.py` |
| 7 | verify clean checkout startup | a fresh `git clone` of the exact commit under test (not this worktree's build state) can run its Req 1 command and reach Req 2 healthy; same localhost-only hostname guard as Req 2 | `test_req7_clean_checkout_startup.py` |
| 8 | Napster documented capabilities/unknowns, no paid calls | `factory-lite/docs/napster-feasibility.md` exists with substantive (non-placeholder, >=15-word), non-empty `## Capabilities`, `## Unknowns`, `## Evidence...` sections; the Evidence section cites at least one `http(s)://` source; the doc explicitly states no live or paid calls were made; no *executable* live-call constructs (`requests.post`/`requests.get`, `fetch(`, `curl `, `authorization: bearer`, `client_secret`) appear -- plainly citing a vendor/API domain (e.g. `developer.napster.com`) as evidence is allowed and expected; no Napster credential files tracked | `test_req8_napster_feasibility.py` |

## Repair R1 (LITE-S1-VERIFY-TESTS-01-R1)

Per Lead's repair assignment, this contract was corrected after the initial
red-run below:
1. Req 8 now rejects empty/placeholder-only sections, requires >=1 HTTP(S)
   evidence citation, and requires an explicit no-live/no-paid-calls
   statement (see `test_required_sections_have_substantive_content`,
   `test_evidence_section_cites_http_source`,
   `test_doc_states_no_live_or_paid_calls_were_made`).
2. `api.napster.com` and plain evidence-domain mentions were removed from
   the live-call marker ban; only executable-call/credential constructs
   remain banned.
3. Req 2 and Req 7 now call `assert_local_health_url()` -- reject any
   documented health URL whose hostname isn't `localhost`/`127.0.0.1`/`::1`
   -- before launching or polling anything. Proven directly by
   `TestLocalHealthUrlGuard` in `test_req2_health_version.py`.
4. This file and the red-run evidence below were updated; the acceptance
   command is unchanged.

## Evidence this contract is red on the exact base

Original run against base SHA `32e8c6f07933737393ea22e729f1a134dae7039d`
(no `app/` and no `factory-lite/docs/` exist yet at this commit):
`factory-lite/tests/evidence/base-32e8c6f0-red-run.txt` -- 20 tests, 12
failures, exit 1.

Repaired contract (R1) run on the same base, same branch, test-only commit
on top: `factory-lite/tests/evidence/base-32e8c6f0-red-run-R1.txt` -- 25
tests, 15 failures, exit 1. Reqs 1, 2, 3, 4, 7, 8 fail because the
documented artifacts they check for do not exist yet -- this includes the
Req 2/7 "service unavailable" path (connection refused / missing doc),
which is the spec's "broken/unavailable service" case occurring naturally
because nothing is implemented. Reqs 5 and 6, plus the new
`TestLocalHealthUrlGuard` fixture tests in Req 2, pass now: Req 5 because
the repo currently has no secrets to find; Req 6 and the URL guard because
their fixtures/inputs are self-contained and prove the harness/guard logic
independent of app state (broken, unavailable, SHA-mismatch, and
non-local-hostname cases are all explicitly asserted nonzero/rejecting).

## No paid/live calls

Every test in this contract only talks to `127.0.0.1`/localhost fixtures,
URLs explicitly asserted local by `assert_local_health_url()`, or the
locally started Stage 1 process; `test_req8` only inspects doc text and
tracked file names (citing a vendor doc URL in text is not a network call).
No external network or paid API calls are made by this suite.

---

# Stage 2 acceptance contract (Verifier-authored, for Lead review)

Translates `factory-lite/spec/stage-2.md` into executable, black-box tests
(`test_s2_req*.py`) layered on top of the unchanged Stage 1 contract above
and the unchanged Stage 1 app. Same acceptance command, same cumulative
run. No application code is included. The spec names the Alex/Dana
rehearsal behavior but does not pin a wire format, so this contract fixes
the following conventions for Builder -- **flag all of these for Lead
review before dispatching Builder**; changing them post-implementation
needs separate rationale per `factory-lite/PROTOCOL.md`.

## Stage 2 rehearsal API (new convention)

Stage 2 is served by the *same* process as Stage 1 (same Req 1 startup
command, same host:port as the Req 2 Health URL with `/health` dropped --
see `s2_helpers.app_base_url()`). New JSON routes, all under
`/api/rehearsal/`:

| Method & path | Body | 200/201 response | Error cases |
|---|---|---|---|
| `POST /api/rehearsal/sessions` | (none) | `{"session_id", "state":"demo", "scenario":"alex_dana", "mode":"offline", "attempt":1}` | -- |
| `POST /sessions/{id}/advance` | `{"to": state}` | `{"state": new_state}` | 409 `invalid_transition` for any `(from,to)` not in `{demo->take_my_seat, take_my_seat->practice}`; 404 for unknown `id` |
| `POST /sessions/{id}/practice` | `{"utterance": str}` | `{"counterpart_reply": str, "hidden_need_revealed": bool}` | 409 `invalid_state` unless current state is `practice` |
| `POST /sessions/{id}/feedback` | (none) | `{"state":"feedback", "evidence_score": int 0-100, "evidence":[{"utterance":str,"note":str},...]}` | 409 unless current state is `practice`; must be replay-safe (re-POST while already in `feedback` never changes the score) |
| `POST /sessions/{id}/retry` | (none) | `{"state":"practice", "attempt": N+1, "pivot_restored": true}` | 409 unless current state is `feedback` |
| `GET /sessions/{id}` | -- | full snapshot: `{"session_id","state","attempt","mode","hidden_need_revealed","transcript":[{"utterance":...},...],"evidence_score"?}` | 404 for unknown `id` |
| `GET /sessions/{id}/attempts` | -- | `{"attempts":[{"attempt":1,"state":...,"evidence_score":...,"transcript":[...]},...]}` -- every prior attempt stays present and unmodified after `retry` | 404 for unknown `id` |

Behavioral conventions fixed by the tests:
- **Hidden need / discovery** (`test_s2_req2_counterpart_hidden_need.py`,
  Repair R1): the hidden need is **composite** -- a hidden budget
  constraint *and* hidden sign-on flexibility -- tracked by the single
  `hidden_need_revealed` boolean. It must be `false` until an utterance in
  that attempt probes *either* side: budget-side (budget/cost/price/
  afford) or sign-on-side ("sign-on", "sign on", "signing bonus",
  "flexible on sign-on", or contract terms generally). A probe from either
  side flips it to `true` and it stays `true` for the rest of that attempt
  regardless of which side triggered it (e.g. a sign-on-only probe with no
  budget keyword at all must reveal it just as a budget probe does). The
  counterpart must retain transcript state turn to turn (not a
  stateless/generic reply).
- **Evidence scoring** (`test_s2_req3_evidence_scoring.py`): every
  `evidence[*].utterance` must be text the user actually sent in that
  attempt (checked as a subset of the attempt's real utterances); score is
  an int in [0, 100] and must not change on repeated reads of the same,
  unmodified attempt (determinism).
- **Retry / pivot** (`test_s2_req4_retry_pivot.py`): `retry` only valid
  from `feedback`; it resets `transcript` to `[]` and `hidden_need_revealed`
  to `false` (discovery must happen again each attempt -- this is the
  "pivot" snapshot), while attempt 1's transcript/score remain retrievable
  and unchanged via `/attempts`.
- **Isolation / replay** (`test_s2_req5_isolation_replay.py`): two open
  sessions never share state; repeated `GET`s are byte-identical; actions
  against a nonexistent `session_id` are always 404, even with other real
  sessions open.
- **Offline mode labeling** (`test_s2_req6_offline_mode.py`): both session
  creation and every snapshot must carry an explicit `"mode": "offline"`
  field -- this must be visible in the API, not only in documentation.
- **UI journey** (`test_s2_req7_ui_journey.py`): the spec's
  "stand-in demonstration -> Take My Seat -> practice -> feedback -> retry"
  language, and MASTER_PROMPT.md's "User watches... takes their seat...
  practices... sees evidence-based feedback and retries", read as an
  end-user UI, not an API-only flow. Convention: the same app serves this
  UI at `/` (the Health URL's root), with these `data-testid` hooks, one
  per state: `start-demo`, `take-my-seat`, `practice-input` (text input),
  `send-utterance`, `feedback-score`, `retry-button`. This is the
  Playwright "real browser journeys" check named in the Verifier mandate.
  **New dev dependency**: this test requires the `playwright` Python
  package plus a downloaded Chromium browser (`pip install playwright &&
  playwright install chromium`) in whatever environment runs the
  acceptance command -- flagging this explicitly since it's a new
  requirement beyond Stage 1's stdlib-only tests. The test `SkipTest`s
  (not a false pass) if `playwright` isn't importable, so its absence is
  visible, not silently green.

## Repair R1 (LITE-S2-VERIFY-TESTS-01-R1)

Per Lead's repair assignment: `stage-2.md` names a hidden need with two
dimensions -- "hidden budget constraint **and** sign-on flexibility" --
but the original contract only tested the budget side. Repair R1:
1. Redefined the hidden need as composite (budget + sign-on) and extended
   the reveal trigger set to sign-on-side probes, as documented in the
   "Hidden need / discovery" bullet above.
2. Added `test_hidden_need_revealed_by_sign_on_only_probe_with_no_budget_keyword`
   in `test_s2_req2_counterpart_hidden_need.py`: a sign-on-only probe with
   no budget/cost/price/afford keyword anywhere still reveals the hidden
   need and it stays revealed for the rest of the attempt.
3. Everything else is unchanged: the `/api/rehearsal/*` wire format, the
   UI served at `/`, the Playwright dependency, and all other Stage 2 test
   files. No Stage 1 file touched; no app code.

## Evidence this contract is red on the exact base

Original run against base SHA `977787ea97068ff942efec8575514c81930b31a7`
(current `dev-v3` head; Stage 1 merged, nothing from Stage 2 implemented):
`factory-lite/tests/evidence/base-977787e-red-run.txt` -- 48 tests total,
25 Stage 1 tests green, 22 Stage 2 failures + 1 Stage 2 error, exit 1.

Repaired contract (R1), same base, same branch, test-only commit on top:
`factory-lite/tests/evidence/base-977787e-red-run-R1.txt` -- see the
Verifier's terminal result for the exact new totals. Every Stage 2 test
fails for a real, legible reason: the `/api/rehearsal/*` routes don't
exist yet, so Flask's own 404 HTML page is returned instead of JSON
(surfaced as a clear `ContractError`, not a silent pass), and the
Playwright journey times out waiting for `data-testid="start-demo"` on
that same 404 page (captured in a screenshot, not committed --
`factory-lite/tests/evidence/screenshots/.gitignore` excludes the PNGs;
local path reported in the Verifier's terminal result). Every Stage 2 test
encodes a specific, deliberately-checked behavior (e.g. "invalid transition
must 409", "unknown session must 404", "hidden need must not leak on
either the budget or sign-on side") and each is failing today precisely
because that behavior doesn't exist yet -- satisfying the "deliberately
failing case" requirement across the whole Stage 2 surface, not just one
isolated fixture.

## No paid/live calls (Stage 2)

Every Stage 2 test talks only to `app_base_url()`, which is derived from
and re-validated by the same `assert_local_health_url()` guard Stage 1
uses (localhost/127.0.0.1/::1 only). The Playwright browser is launched
locally and only ever navigates to that same local URL. No external
network or paid API calls are made.

---

# Stage 3 acceptance contract (Verifier-authored, for Lead review)

Translates `factory-lite/spec/stage-3.md` into executable tests
(`test_s3_req*.py`) plus one deliberately separate, gated live module
(`test_s3_live_napster.py`), layered on the unchanged Stage 1-2 contract
and app. **This contract never makes a vendor API call itself.** No
application code is included. Flag all conventions below for Lead review
before Builder starts.

## Research done before writing any test (per stage-3.md "verify current
vendor docs ... before coding")

Official Napster documentation was read (fetch only, no signup/login/API
call) and compiled into
`factory-lite/docs/stage3-capability-record.md`, citing:
`developers.napster.com/docs/introduction/{authentication,limits}`,
`.../building-your-omniagent/companion`, and five 2026
`.../whats-new/platform-api/*` changelog entries. Key findings: Napster's
"Companion" product covers avatar/visual-identity and voice (including
cloning a voice *from a submitted reference video's own audio track*, not
from a live user); "handoff" is documented **only** as SIP-telephony call
transfer between extensions; **no meeting-join, meeting-relay, or
meeting-control capability of any kind is documented anywhere** (the
words "Zoom", "Teams", "Meet", "meeting" do not appear on any page read);
account-capability gates are explicit named errors
(`CompanionV2NotEnabled`, `ProviderNotEnabled`, `InactiveSubscription`,
etc.) that must be checked live, not assumed; no pricing/free-tier is
documented. `docs.napster.ai` was attempted and failed (redirect loop) --
not used as a source. See that file for full citations and the explicit
list of unknowns.

## Fixed conventions

| Req | Spec text | Convention fixed by this contract | Test file |
|---|---|---|---|
| capability record | vendor docs + account capability before coding | `factory-lite/docs/stage3-capability-record.md` with substantive, non-placeholder `## Capabilities`/`## Unknowns`/account-capability sections, >=1 official evidence URL, explicit "no live API calls / no credentials / no cost" statement, and account capability explicitly marked **unverified** pending a live check | `test_s3_req1_capability_record.py` |
| mock insufficient / certification gate | "mock tests separate and insufficient for stage certification"; PROTOCOL.md "No certification for missing evidence" | `factory-lite/docs/stage3-certification-status.md` must read **NOT CERTIFIED** and track exactly 4 named gates (live authorization, credentials present, account capability confirmed, redacted real evidence captured) until all 4 have evidence | `test_s3_req2_certification_gate.py` |
| duplicate sessions / cleanup on error | reject duplicate sessions, cleanup on error | `factory-lite/tests/s3_live_gate.py`'s `SessionRegistry`: at most one active session per capability name, `cleanup()` guaranteed exactly once on success or exception. This is harness-level logic the live probe must use -- **no new HTTP endpoint is introduced for this**; see risk note below | `test_s3_req3_session_lifecycle.py` |
| bounded retry for 409/429 | bounded retry for 409/429 | `s3_live_gate.call_with_bounded_retry`: retries only 409/429, stops after `MAX_RETRIES=3` additional attempts (4 total), any other status returned as-is, never raises on the caller's behalf | `test_s3_req4_bounded_retry.py` |
| denied mic fallback | denied mic fallback | Stage 3 adds `data-testid="voice-practice-toggle"` to the existing Stage 2 UI at `/`; on mic denial (the default for a fresh, ungranted browser context), `data-testid="mic-denied-fallback"` becomes visible while `data-testid="practice-input"` stays usable | `test_s3_req5_mic_denied_fallback.py` (Playwright, reuses Stage 2's `s2_helpers`) |
| no invented voice cloning / relay control | forbid fabricated capability claims | static scan of every git-tracked file for first-person claims of joining/controlling a live meeting or cloning a real user's voice (quoting Napster's own documented video-to-voice cloning is explicitly allowed) | `test_s3_req6_no_fabrication_claims.py` |
| authorized live probe | "authorized bounded live probe for companion/avatar, audio and handoff"; redacted evidence; real embodied demonstration + practice | `test_s3_live_napster.py`, run only via `py -3.12 -m unittest factory-lite.tests.test_s3_live_napster -v`. Gate: `SAH_NAPSTER_LIVE=1` **and** `NAPSTER_API_KEY` (see `s3_live_gate.REQUIRED_CREDENTIAL_ENV_VARS`) must both be set, or every test in the module is skipped with an explicit, non-certifying message. The live probe body is intentionally a stub that **fails loudly** rather than fabricate a pass -- it must be replaced with a real, bounded-retry, cleanup-guaranteed call that writes a redacted evidence record via `write_redacted_evidence()` (schema: `s3_live_gate.REDACTED_EVIDENCE_SCHEMA_FIELDS`) before any claim of real embodied demonstration/practice can be made | `test_s3_live_napster.py` |

## Contract risks for Lead review

1. **No new HTTP wire format was introduced for the live-probe session
   lifecycle/retry** (unlike Stage 2's `/api/rehearsal/*`). The spec
   doesn't say whether the real Napster integration should be brokered
   through a new server-side endpoint or driven more directly from the
   client/Builder's own integration code, so this contract proves the
   *session-registry and retry logic* as reusable, vendor-agnostic test
   tooling (`s3_live_gate.py`) rather than inventing an HTTP contract for
   it. If Builder's design needs a new endpoint, review that design
   against these same invariants (one session per capability, cleanup
   guaranteed, bounded retry) at implementation-review time.
2. `test_s3_live_napster.py` matches `test_*.py`, so the cumulative
   `discover` command also collects it; without the gate it reports as
   **skipped** there (not failed), which does not change that command's
   pass/fail status. This is intentional, not an oversight.
3. The mic-denied-fallback convention adds one new UI control
   (`voice-practice-toggle`) to the existing Stage 2 page; if Builder's
   real voice UX differs, this `data-testid` convention needs revisiting
   before Builder starts, same as any other UI convention in this file.
4. `factory-lite/docs/stage3-capability-record.md` and
   `test_s3_req1/2_*.py` already pass today (like Stage 1's req5/req6 and
   Stage 2's req5/req6) because the Verifier produced the required
   documentation research and certification-status tracking as part of
   this assignment, per Lead's explicit instruction to research vendor
   docs now, not defer it to Builder. The overall contract is still red
   on the exact base because every other Stage 3 behavior genuinely
   doesn't exist yet.

## Evidence this contract is red on the exact base

Run against base SHA `b0e276d52db7cdac643206b65c137b75f2ff251a` (current
`dev-v3` head at the time of this assignment; Stage 1-2 merged, nothing
from Stage 3 implemented):
`factory-lite/tests/evidence/base-b0e276d-red-run.txt`. See the
Verifier's terminal result for exact counts; Stage 1+2's 49 tests remain
green, the new `test_s3_req5_mic_denied_fallback` fails/errors against the
real app's missing UI control, and `test_s3_live_napster`'s 3 probes show
as skipped (gate absent) -- all while `test_s3_req1/2/3/4/6` already pass
as harness/documentation proofs, per risk note 4 above.

## No paid/live calls (Stage 3)

No test file in this contract -- including `test_s3_live_napster.py`
without the gate -- makes a vendor API call, logs in, or spends credit.
`s3_live_gate.py`'s retry/session-registry proofs use local Python
callables as fixtures, never a network call. The mic-fallback Playwright
test only talks to the same localhost app URL as Stage 1-2. The Verifier
has never set `SAH_NAPSTER_LIVE=1` and has never run the live-only
command with the gate enabled.
