# Stage 4B acceptance contract (consent, vendor lifecycle, deletion)

**Task:** `LITE-S4B-VERIFY-TESTS-01`
**Base:** `baa33b39bb043d37363e4ff5d0c2ea2acd0bb4f8` (`dev-v3`, Stage 4A certified)
**Author:** Stage 4A/4B Verifier (tests and docs only)
**Status:** deliberate-red contract for Lead review before any Builder assignment.
**Scope:** Stage 4B consent and data lifecycle only. 4C (responsive UI,
packaging) is out of scope, as are Playwright, media capture, credentials,
biometrics, live/paid calls, deployment and submission.

This document fixes the wire conventions asserted by
`factory-lite/tests/test_s4b_*.py`. It adds no application code and edits no
pre-existing test or helper. Every product claim is proved by direct black-box
HTTP behaviour against the real application; the only non-product check is
`test_s4b_contract_selfcheck.py`, which rejects skips, placeholders and
passing-default assertions.

## 1. Preservation and run command

All 161 certified Stage 1-4A tests and their helpers are unchanged. The
cumulative command is unchanged:

```
py -3.12 -m unittest discover -s factory-lite/tests -p "test_*.py" -v
```

The 4B suite must be red on the base (consent and deletion routes absent, no
consent gating, no retained-handle persistence) and green only after Builder
implements this contract.

## 2. Granular consent (`sah.consent.v1`)

Six scopes, exactly and separately: `rehearsal`, `avatar`, `mic`,
`transcript_save`, `research`, `subject_consent`.

A consent record is created with the session, so every scope has an explicit
decision (default denied) before any vendor is initialized. `subject_consent`
is not applicable in v1.

`GET /api/rehearsal/sessions/{id}/consent` returns **200**:

```json
{
  "schema": "sah.consent.v1",
  "policy_version": "consent.v1",
  "session_hash": "sha256:<hex sha256 of the UTF-8 session id>",
  "scopes": {
    "rehearsal":       {"granted": false, "applicable": true,  "recorded_at_utc": null},
    "avatar":          {"granted": false, "applicable": true,  "recorded_at_utc": null},
    "mic":             {"granted": false, "applicable": true,  "recorded_at_utc": null},
    "transcript_save": {"granted": false, "applicable": true,  "recorded_at_utc": null},
    "research":        {"granted": false, "applicable": true,  "recorded_at_utc": null},
    "subject_consent": {"granted": false, "applicable": false, "recorded_at_utc": null}
  }
}
```

Unknown session: **404** `not_found`.

`POST /api/rehearsal/sessions/{id}/consent` body:

```json
{"schema": "sah.consent.v1", "scope": "avatar", "granted": true}
```

**200** response:

```json
{"schema": "sah.consent.v1", "scope": "avatar", "granted": true,
 "policy_version": "consent.v1", "recorded_at_utc": "<ISO-8601 Z>",
 "session_hash": "sha256:<same hash as GET>"}
```

Rejections are typed and change no scope:

| Condition | Status | `error` |
|---|---|---|
| `schema != "sah.consent.v1"` | 400 | `invalid_consent_schema` |
| `scope` not one of the six | 400 | `invalid_scope` |
| `granted` not a JSON boolean | 400 | `invalid_consent` |
| `scope == subject_consent` and `granted == true` | 409 | `subject_consent_not_applicable` |
| unknown session | 404 | `not_found` |

Scopes never bundle: granting `avatar` must not change `rehearsal`, `mic`,
`transcript_save`, `research` or `subject_consent`, and vice versa.

## 3. Consent gates on operations

An operation whose required scope is not granted returns **403** with
`{"error": "consent_required", "scope": "<scope>"}` and performs no work (no
vendor call, no saved transcript, no export, no microphone state).

| Operation | Route | Required scopes, in order |
|---|---|---|
| Vendor session create | `POST /api/rehearsal/sessions/{id}/napster-session` | `rehearsal`, then `avatar` |
| Microphone start | `POST /api/rehearsal/sessions/{id}/mic/start` | `mic` |
| Save transcript | `POST /api/rehearsal/sessions/{id}/transcript/save` | `transcript_save` |
| Research export | `POST /api/rehearsal/sessions/{id}/research/export` | `research` |

Success shapes:

- `mic/start` → 200 `{"status": "started", "scope": "mic", "synthetic": true}`.
- `transcript/save` → 200 `{"saved": true, "retention_hours": 24, "session_hash": "sha256:..."}`;
  `GET /api/rehearsal/sessions/{id}/transcript/saved` returns **200**
  `{"schema": "sah.transcript_saved.v1", "session_hash": "...", "transcript": [...]}`
  while a saved copy exists, otherwise **404** `not_found`.
- `research/export` → 200 `{"exported": true, "deidentified": true, "aggregate": {"turns": <int>}}`;
  the response must contain no user utterance text.
- Text practice (`POST .../practice`) remains available when `avatar` or `mic`
  is denied.

## 4. Withdrawal mid-session

Withdrawal is the same route with `"granted": false`; it is immediate and
returns 200. Effects:

| Withdrawn scope | Effect |
|---|---|
| `avatar` | any live vendor session is torn down with exactly one upstream DELETE; later vendor create is 403 `consent_required` `avatar`; text practice still works |
| `transcript_save` | the saved transcript copy is deleted; `GET .../transcript/saved` becomes 404 |
| `mic` | `mic/start` becomes 403 `consent_required` `mic` |
| `research` | `research/export` becomes 403 `consent_required` `research` |
| `rehearsal` | the session ends: `GET /sessions/{id}` reports `state == "ended"`, practice is 409 `invalid_state`, any live vendor is torn down |
| `subject_consent` | not applicable in v1; only `granted: false` is accepted |

## 5. Application-connected fake vendor

The app reaches the vendor only through configuration, using the existing
Stage 3 names: `NAPSTER_BASE_URL`, `NAPSTER_API_KEY`, `NAPSTER_AGENT_ID`.
Create is `POST {base}/public/agents/{agent}/connections`; delete is
`DELETE {base}/public/connections/{connection_id}`. The fake vendor is a test
fixture (`factory-lite/tests/s4b_helpers.py`); the application never imports
it and never contacts the real Napster.

`SAH_STATE_DIR` (optional, default unset) names a directory where the app
persists retained vendor handles so a restarted process can still delete them.
No token or raw API key may be written there — only the connection id, base
URL and agent id needed for teardown.

Exactly-once rules:

1. A successful create produces exactly one upstream record and one persisted
   handle for the session.
2. Deleting the session sends exactly one upstream DELETE for that handle; a
   second delete sends no further upstream DELETE and does not 500.
3. If create succeeds but the operation fails (`simulate_error:
   "post_allocation_failure"` with a vendor whose DELETE fails), the response
   is 502 with `connection_retained: true`, the upstream record count stays 1,
   and the handle is retained for cleanup.
4. A later cleanup retries the retained handle exactly once, returns 200 (never
   500) and clears the handle. The vendor record count never exceeds 1.
5. After an app restart with the same `SAH_STATE_DIR`, `DELETE
   /api/rehearsal/sessions/{id}` must still delete the persisted handle
   exactly once and return a cleanup receipt; a second delete does not 500.

## 6. Deletion completeness and receipt (`sah.cleanup.v1`)

`DELETE /api/rehearsal/sessions/{id}` returns **200**:

```json
{
  "schema": "sah.cleanup.v1",
  "session_hash": "sha256:<hex sha256 of the UTF-8 session id>",
  "vendor_session_destroyed": true,
  "local_media_stopped": true,
  "transcript_deleted": true,
  "connection_retained": false,
  "attempts": 1,
  "completed_at": "<ISO-8601 Z>",
  "redacted": true,
  "already_deleted": false
}
```

- After a successful delete, `GET /api/rehearsal/sessions/{id}` is **404** and
  the saved transcript copy is gone.
- A second `DELETE` returns **200** (`already_deleted: true`) or **404**; never
  5xx.
- `session_hash` is the only session identifier in the receipt; the raw
  `session_id` never appears in it.
- If vendor teardown fails, the receipt reports `vendor_session_destroyed:
  false`, `connection_retained: true`; local state is still deleted (`GET`
  404) and a later `DELETE` retries the retained handle and reports success.
- With no vendor session, the receipt reports `vendor_session_destroyed: true`
  and `connection_retained: false` (nothing is left live).
- After deletion, the application log contains no user utterance text, no
  vendor token, no vendor connection id, and no API key value.

## 8. Deliberate-red evidence (unchanged application at the assigned base)

All gate runs below were executed by the independent Verifier on
`baa33b39bb043d37363e4ff5d0c2ea2acd0bb4f8` with a clean tree. The 4B modules
are red because the consent, lifecycle and deletion routes and gates do not
exist yet; no application code was touched.

| Gate | Command | Result | Exit |
|---|---|---|---|
| Exact-base preflight (no 4B files) | `py -3.12 -m unittest discover -s factory-lite/tests -p "test_*.py" -v` | `Ran 161 tests`, `OK (skipped=1)`, 2102.1 s | 0 |
| 4B focused suite | `py -3.12 -m unittest discover -s factory-lite/tests -p "test_s4b_*.py" -v` | `Ran 25 tests`, `FAILED (failures=23)`, 0 errors, 172.4 s | 1 |
| Cumulative | `py -3.12 -m unittest discover -s factory-lite/tests -p "test_*.py" -v` | `Ran 186 tests`, `FAILED (failures=23, skipped=1)`, 0 errors, 1368.1 s | 1 |

The cumulative failure set is identical to the focused set (23 unique, all in
`test_s4b_req1..req3`); the 161 certified Stage 1-4A tests stay green with their
single pre-existing skip, and the two 4B self-checks pass. Evidence files:

- `factory-lite/tests/evidence/lite-s4b-verify-tests-01-base-baa33b3-preflight.txt`
- `factory-lite/tests/evidence/lite-s4b-verify-tests-01-focused-red.txt`
- `factory-lite/tests/evidence/lite-s4b-verify-tests-01-focused-red-inventory.txt`
- `factory-lite/tests/evidence/lite-s4b-verify-tests-01-cumulative-red.txt`

Syntax/import gate: `py -3.12 -m py_compile` over `s4b_helpers.py` and the four
`test_s4b_*.py` modules exits 0.

Environment note: on Windows, start the app and suite from a normal `C:\...`
path. `python` must resolve to an interpreter with the app dependencies
(Flask); prepend the project Python 3.12 directory if the default `python` on
PATH lacks them. `/health` must report the worktree HEAD.

## 9. Safety of the test suite

Every helper talks only to the localhost application URL from `app/RUN.md`
(guarded by `assert_local_health_url`) and to a loopback fake vendor on an
ephemeral port. No credential is read, no biometric data is created, no media
is captured, and no live or paid call is made. The fake vendor is test-owned
and is the only non-application server involved.
