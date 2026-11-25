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
| 2 | health/version reports actual build SHA | `app/RUN.md` also has a `## Health` heading whose fenced block's first line is the full health URL (e.g. `http://127.0.0.1:8000/health`); that endpoint returns HTTP 200 JSON `{"status": "ok", "version": "<git HEAD sha>"}` | `test_req2_health_version.py` |
| 3 | container non-root | `app/Dockerfile` builds, and `docker run <image> id -u` reports a non-zero UID | `test_req3_container_nonroot.py` |
| 4 | dependency lock | `app/` contains a non-empty recognized lock file (`requirements.lock`, `poetry.lock`, `Pipfile.lock`, `uv.lock`, `package-lock.json`, `pnpm-lock.yaml`, or `yarn.lock`) | `test_req4_dependency_lock.py` |
| 5 | no secrets in repo | no git-tracked file matches common secret patterns (private keys, AWS/OpenAI/Stripe-style keys, `secret=`/`password=`/`api_key=` literals); no tracked `.env`-like file outside `.env.example`/`.env.sample`/`.env.template` | `test_req5_no_secrets.py` |
| 6 | independent harness exits nonzero for broken service, zero for healthy | `factory-lite/tests/harness/health_check.py` is a dependency-free CLI harness; proven against fixtures (healthy / 500 / unavailable / SHA-mismatch) under this test's own control | `test_req6_harness_contract.py` |
| 7 | verify clean checkout startup | a fresh `git clone` of the exact commit under test (not this worktree's build state) can run its Req 1 command and reach Req 2 healthy | `test_req7_clean_checkout_startup.py` |
| 8 | Napster documented capabilities/unknowns, no paid calls | `factory-lite/docs/napster-feasibility.md` exists with `## Capabilities`, `## Unknowns`, `## Evidence...` sections and no live-call markers (`requests.*`, `fetch(`, `curl `, `api.napster.com`, bearer/client_secret strings); no Napster credential files tracked | `test_req8_napster_feasibility.py` |

## Evidence this contract is red on the exact base

Run against base SHA `32e8c6f07933737393ea22e729f1a134dae7039d` (no `app/`
and no `factory-lite/docs/` exist yet at this commit): the full discover run
exits nonzero. Reqs 1, 2, 3, 4, 7, 8 fail because the documented artifacts
they check for do not exist yet -- this includes the Req 2/7 "service
unavailable" path (connection refused / missing doc), which is the spec's
"broken/unavailable service" case occurring naturally because nothing is
implemented. Reqs 5 and 6 pass now: Req 5 because the repo currently has no
secrets to find, and Req 6 because its fixtures are self-contained and prove
the harness logic independent of app state (including an explicit
broken-service and an explicit unavailable-service fixture, both asserted
nonzero). See the Verifier's terminal report for the exact command output
and evidence log path.

## No paid/live calls

Every test in this contract only talks to `127.0.0.1`/localhost fixtures or
the locally started Stage 1 process; `test_req8` only inspects doc text and
tracked file names. No external network or paid API calls are made by this
suite.
