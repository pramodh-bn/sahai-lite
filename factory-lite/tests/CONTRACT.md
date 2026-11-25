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
