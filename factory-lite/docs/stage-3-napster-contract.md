# Stage 3 Napster Embodied Integration Contract & Feasibility

## 1. Overview and Authoritative References

This document establishes the verified technical contract, architecture, and evidence schema for Stage 3 (Napster embodied integration) in Sahai Lite, translating `factory-lite/spec/stage-3.md` and `factory-lite/PROTOCOL.md` into concrete, executable black-box requirements.

Authoritative external references:
- **Official Napster Developer Documentation**: [https://developers.napster.com/docs](https://developers.napster.com/docs)
- **Official Napster Ignite Hackathon Guide**: [https://www.napster.com/ignite-hackathon-guide](https://www.napster.com/ignite-hackathon-guide)
- **Historical Live-Tested Reference**: `D:\Workspace\koehashi` branch `stage-5` (including `stage-5/vendors.py`, `stage-5/lib/PROVENANCE.md`, `stage-5/server.py`, `harness/test_face_speech.py`, and `harness/stage5.py`).

*Note on status*: Stage 3 remains explicitly **UNCERTIFIED**. Mock and offline verification are strictly insufficient for Stage 3 certification. Full certification requires an authorized live run with real credentials under `SAH_NAPSTER_LIVE=1` producing verified, redacted live evidence.

---

## 2. Base Host Configurability, Source Boundary & Dual Host Policy

The contract establishes two distinct host policies:
1. **Offline / Mock Mode (`mode='offline'`)**:
   - Local fake-vendor fixtures and offline tests may use loopback (`127.0.0.1`, `localhost`) or historical references (`https://napster-api.napster.com`).
   - The server-side adapter uses `https://companion-api.napster.com` as the default base host while keeping `NAPSTER_BASE_URL` configurable via environment variables for fake-vendor testing.
2. **Credentialed Certification (`SAH_NAPSTER_LIVE=1`, `mode='live'`)**:
   - Must strictly require HTTPS and the exact approved real host: `companion-api.napster.com`.
   - Rejects `localhost`, loopback (`127.0.0.1`), private / link-local / test / documentation IPs (e.g. `10.x`, `192.168.x`, `172.16-31.x`, `169.254.x`, `192.0.2.x`, `198.51.100.x`, `203.0.113.x`), non-HTTPS URLs, userinfo, non-default ports, DNS aliases, and every other host.
   - Historical `napster-api.napster.com` remains reference-only and non-certifying unless separately authorized by the owner.
   - The evidence validator independently enforces this boundary: loopback evidence is valid only in explicit mock/offline mode, but `validate_stage3_evidence(..., mode='live')` and `is_stage3_certified(..., mode='live')` reject it.

---

## 3. Server-Side Adapter & Session Creation Contract

To ensure security and keep credentials isolated:
1. **Zero Credential Exposure**: `NAPSTER_API_KEY` (and `X-Api-Key`) is held strictly server-side. It is never exposed in browser payloads, HTTP responses, query parameters, client-side bundles, application logs, or test evidence.
2. **Session Creation Route**:
   - `POST /api/rehearsal/sessions/{id}/napster-session`
   - Accepts optional JSON: `{"channel_type": "webrtc", "simulate_error": str}` (defaulting to `"webrtc"`).
3. **Upstream Request**:
   - URL: `{NAPSTER_BASE_URL}/public/agents/{NAPSTER_AGENT_ID}/connections`
   - Method: `POST`
   - Headers: `X-Api-Key: <NAPSTER_API_KEY>`, `Content-Type: application/json`, `User-Agent: sahai-lite/1.0`
   - Payload:
     ```json
     {
       "channelType": "webrtc",
       "externalClientId": "sahai_<rehearsal_session_id_prefix>"
     }
     ```
4. **Response Parsing & Downstream Token Delivery**:
   - Parses upstream JSON: extracting short-lived connection `token` and `connection.id`.
   - Returns to browser: `{"token": "<ephemeral_token>", "connection_id": "<conn_id>", "status": "ready"}`.
5. **Teardown / Cleanup Route**:
   - `DELETE /api/rehearsal/sessions/{id}/napster-session`
   - Deterministically destroys active WebRTC sessions and releases local resources via an observable ledger.

---

## 4. Fake Vendor Harness, Retries, Single-Flight & Cooldown

Local fake-vendor tests assert robust network behavior without live vendor dependencies:
- **Bounded Retry**: Exactly one retry attempt (maximum 2 attempts total) allowed only for transient upstream rate-limiting (`429`) or concurrency conflict (`409`). Each retry test case must run against an isolated fresh rehearsal session with explicit teardown.
- **No Retry on Client / Server Errors**: Errors such as `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, or `500 Internal Server Error` must fail immediately with no retry attempts.
- **Concurrent Single-Flight Duplicate Rejection**: Verified using controlled blocking in the fake vendor. When a connection request is in flight, any concurrent request for the same rehearsal session must deterministically return `409 Conflict`, ensuring only a single upstream creation call is made.
- **Failure Cooldown**: Following a failed connection attempt, immediate rapid re-triggering is gated by cooldown (returning `409` or `429`) to prevent vendor hammering.
- **Observable Cleanup Ledger & Automatic Rollback**: The fake vendor maintains an observable ledger (`created`, `deleted`, `active`). When a post-allocation error occurs (e.g. simulated via `simulate_error="post_allocation_failure"` or downstream initialization failure), the app adapter must automatically issue an upstream vendor `DELETE` to roll back the allocated connection (`created=1, deleted=1, active=0`) without requiring an explicit client teardown request.

---

## 5. End-User UI Journey & Microphone Fallback

The end-user UI extends Stage 2's rehearsal journey at `/`:
1. **Flow**: `demo` -> `take_my_seat` -> `practice` -> `feedback` -> `retry`.
2. **Opt-in Napster Avatar**:
   - Avatar connection is strictly **opt-in**. The page does not load WebRTC bundles or open signaling websockets automatically.
   - `[data-testid="napster-connect"]`: Button to initiate live avatar connection.
   - `[data-testid="napster-avatar"]`: Container slot for the mounted avatar `<video>` and `<audio>`.
   - `[data-testid="napster-status"]`: Displays honest live status ("disconnected", "connecting", "connected", "offline fallback").
3. **Honest Offline / Fallback Labeling**:
   - When running in offline or mock mode, UI elements visibly label the avatar as "offline" or "fallback". No false claims of live connection are permitted.
4. **Denied Microphone Fallback**:
   - If the user denies browser microphone permissions (or audio devices are missing), the UI displays a clear notice: `[data-testid="mic-denied-fallback"]`.
   - Text practice remains fully functional: `[data-testid="practice-input"]` and `[data-testid="send-utterance"]` remain active and usable.
5. **Deterministic Cleanup**:
   - `[data-testid="napster-disconnect"]` resets the avatar slot, stops media tracks, and cleanly tears down the session.

---

## 6. App-Local Handoff & Prohibited Capabilities

The Sahai handoff is strictly application-local:
- The stand-in embodied avatar demonstrates the negotiation scenario (Alex and Dana) in state `demo`.
- The user takes their seat via `POST /api/rehearsal/sessions/{id}/advance` with `{"to": "take_my_seat"}` and then `{"to": "practice"}`.
- **Strictly Prohibited**:
  - No SIP URIs, telephony dialing, or PSTN transfer (`sip:`, `tel:`).
  - No meeting join, bot attendance, or relay control (Zoom, Teams, Google Meet, Chime bots).
  - No real-person voice cloning or voiceprint replication.

---

## 7. Live-Only Gate & Certification Boundary

To protect resources and comply with budget boundaries:
- A separate immutable test module (`factory-lite.tests.test_s3_req7_live_gate`) guards live vendor calls.
- **Stable Live Test Command**:
  ```
  py -3.12 -m unittest factory-lite.tests.test_s3_req7_live_gate -v
  ```
- **Prerequisites**: `SAH_NAPSTER_LIVE=1`, `NAPSTER_API_KEY`, and `NAPSTER_AGENT_ID`.
- **Gate Absent**: Automatically skips with an explicit non-certifying skip message, exiting 0 with zero vendor calls and creating zero artifacts.
- **Gate Open**: Drives the real app and browser, requiring exact inspectable status `readyVideo` and exact callback argument `onAvatarReady(true)` (neither inferred from generic text or the other). Requires mounted `<video>` and `<audio>` elements, where the mounted `<audio>` element itself owns an active live audio track (no fallback to video stream). A mere HTTP 200/token cannot certify. Missing Playwright or browser runtime under an open gate is a hard non-certifying block/failure, never a skip.
- **Non-Certifying Mock Boundary**: Mock vendor success or offline test runs are explicitly declared insufficient for Stage 3 certification.

---

## 8. Real Evidence Schema & Redaction

Every Stage 3 evidence record must adhere to the following schema:
- `start_time_utc` and `end_time_utc`: Valid non-null ISO-8601 UTC strings. Synthetic timestamps (e.g. 1970/2000 epoch or future timestamps) are strictly rejected.
- `probe_correlation_hash`: 64-character lowercase hex SHA-256 string.
- `http_probe`: Dictionary with `host`, `path`, `method`, and `status_code`. In `mode='live'`, `host` must strictly be `companion-api.napster.com` with HTTPS scheme.
- `ready_proof`: `{"event": "onAvatarReady", "avatar_ready": true, "status": "readyVideo"}`.
- `media_proof`: `{"video_mounted": true, "audio_mounted": true, "video_track_live": true, "audio_track_live": true}`.
- `cleanup_proof`: `{"session_destroyed": true, "resources_released": true}`.
- `redacted`: Strictly boolean `true`.
- **Strict Redactions**: Raw API keys, Bearer tokens, JWT tokens, unredacted agent/connection IDs, rehearsal transcripts, user utterances, and placeholder markers ("TODO", "TBD", "fixture") are completely rejected.

---

## 9. SDK Provenance & Demo Path Constraints

- **Package**: `@touchcastllc/napster-companion-api`
- **Version**: `2.0.0` (frozen, non-floating)
- **SHA-256**: `c1b2db52267af46e172e4c5fbb0c46b67f57729bc841b26ac4e112a14ddd025f`
- **Global**: `window.napsterCompanionApiSDK`
- **Execution Budget**: Reliable end-to-end demo path bounded to `<= 180 seconds` (3 minutes).
- **No Deploy / Submit**: External deployment scripts, cloud triggers, and submission actions are forbidden.

---

## 10. Stage 3 Cycle 5 Live-Contract Verification (LITE-S3-LIVE-CONTRACT-02)

Under assignment `LITE-S3-LIVE-CONTRACT-02`, the live contract and evidence validation are hardened with strict live-only host policy enforcement and safety guarantees:
1. **Live-Only Host Policy Enforcement**:
   - Credentialed certification (`mode='live'`) strictly enforces HTTPS and exact approved real host `companion-api.napster.com`.
   - Rejects loopback (`127.0.0.1`, `localhost`), private/link-local/test/documentation IPs, non-HTTPS URLs, userinfo, non-default ports, DNS aliases, and historical references (`napster-api.napster.com`).
   - The evidence validator independently enforces this policy: `validate_stage3_evidence(..., mode='live')` and `is_stage3_certified(..., mode='live')` reject loopback and non-approved hosts with descriptive non-certifying validation errors.
2. **Single Browser-Owned Flow & Direct Preallocation Prohibition**:
   - The live test executes exactly one browser-owned session creation and connection flow. Direct preallocation via `post_napster_session` is strictly prohibited and statically rejected by the meta-contract self-check.
3. **Request-Observed Accounting & In-Memory Redaction**:
   - Outgoing connection POST and DELETE operations are counted strictly from observed HTTP requests via `page.on("request")`. Raw tokens and credentials are never stored, logged, or printed.
   - The upstream connection ID is hashed immediately with SHA-256 (`probe_correlation_hash`) and the vendor route is recorded in redacted format (`/public/agents/[REDACTED]/connections`). The observed POST response status must strictly equal 200 without fallback default substitution (`or 200`).
4. **Monotonic Deadline & Remaining-Time Budgeting**:
   - A 30.0-second monotonic deadline is established at live-test start. All Playwright page navigations, element waits, response observations, clicks (`connect_btn.click()`, `disconnect_btn.click()`), and teardown steps consume only the remaining monotonic milliseconds.
   - A dedicated 5.0-second cleanup reserve ensures that if the budget is exhausted before teardown, waiting halts immediately and bounded cleanup executes.
5. **Predicate Synchronization via `page.wait_for_function`**:
   - Readiness checks (exact status `readyVideo`, callback argument `onAvatarReady(true)`, mounted live `<video>`, audio-element-owned live track) and post-disconnect release checks (zero live tracks, cleared media, `avatarReady=false`, `sdkStatus=unavailable`) use deadline-bound `page.wait_for_function` calls to prevent asynchronous races with vendor SDK callbacks and DOM teardown.
6. **Deterministic Disconnect & Exactly-Once Cleanup Guard**:
   - Disconnect observation uses Playwright's `expect_response` bound to the application's DELETE request. The `cleanup_attempted['sent']` flag is set only upon observing the outgoing DELETE request.
   - The `finally` fallback issues a DELETE only if no cleanup request was attempted, passing the remaining monotonic cleanup timeout to `delete_napster_session`.
   - If connection creation was observed over the network but no session ID is available for fallback, or if cleanup fails/becomes indeterminate, certification fails prominently reporting possible retained upstream resources (with zero test retries).
7. **Fresh Evidence Target & Temporary File Cleanup**:
   - Under an open live gate, if `SAH_STAGE3_EVIDENCE_PATH` already exists prior to test execution, the run fails immediately before initiating application or vendor flows. Temporary staging files created during atomic writes are cleaned up if writing fails.
8. **Non-Sensitive Operational Telemetry & Atomic Delivery**:
   - Evidence records `connection_create_requests: 1`, `cleanup_requests: 1`, and measured `active_duration_seconds: <= 30.0`. Validated via `validate_stage3_evidence(evidence, mode='live')` and `is_stage3_certified(evidence, mode='live')` before atomic replacement to `SAH_STAGE3_EVIDENCE_PATH`. Under gate-absent conditions, the test skips explicitly with zero calls and creates no files.
9. **Strengthened 4-Test Meta-Contract Verification**:
   - `factory-lite/tests/test_s3_contract_selfcheck.py` maintains exactly 4 tests, verifying module imports, helper keyword compatibility (including `simulate_error` on `post_napster_session`, `timeout` on `delete_napster_session`, and `mode` on `validate_stage3_evidence`), absence of placeholder assertions, and comprehensive static structural checks for all live gate invariants and host policy rules.
