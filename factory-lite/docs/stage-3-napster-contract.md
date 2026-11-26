# Stage 3 Napster Embodied Integration Contract & Feasibility

## 1. Overview and Authoritative References

This document establishes the verified technical contract, architecture, and evidence schema for Stage 3 (Napster embodied integration) in Sahai Lite, translating `factory-lite/spec/stage-3.md` and `factory-lite/PROTOCOL.md` into concrete, executable black-box requirements.

Authoritative external references:
- **Official Napster Developer Documentation**: [https://developers.napster.com/docs](https://developers.napster.com/docs)
- **Official Napster Ignite Hackathon Guide**: [https://www.napster.com/ignite-hackathon-guide](https://www.napster.com/ignite-hackathon-guide)
- **Historical Live-Tested Reference**: `D:\Workspace\koehashi` branch `stage-5` (including `stage-5/vendors.py`, `stage-5/lib/PROVENANCE.md`, `stage-5/server.py`, `harness/test_face_speech.py`, and `harness/stage5.py`).

*Note on status*: Stage 3 remains explicitly **UNCERTIFIED**. Mock and offline verification are strictly insufficient for Stage 3 certification. Full certification requires an authorized live run with real credentials under `SAH_NAPSTER_LIVE=1` producing verified, redacted live evidence.

---

## 2. Base Host Configurability & Alias Differences

Research across official documentation and historical live code reveals domain alias differences:
- **Official current documentation**: References REST endpoints under `https://api.napster.com` and developer portal tools at `https://developers.napster.com`.
- **Historical live service**: Validated against `https://napster-api.napster.com` for agent connection creation, with browser WebRTC signaling routed to `wss://avatar-signaling.napster.ai`.

**Architectural Decision**: The server-side adapter must not hardcode either domain. The base host must remain strictly configurable via the `NAPSTER_BASE_URL` environment variable (defaulting to `https://napster-api.napster.com` or `https://api.napster.com`), permitting seamless routing to local test fixtures and accommodating any upstream DNS/domain alias variations without assumptions or code edits.

---

## 3. Server-Side Adapter & Session Creation Contract

To ensure security and keep credentials isolated:
1. **Zero Credential Exposure**: `NAPSTER_API_KEY` (and `X-Api-Key`) is held strictly server-side. It is never exposed in browser payloads, HTTP responses, query parameters, client-side bundles, application logs, or test evidence.
2. **Session Creation Route**:
   - `POST /api/rehearsal/sessions/{id}/napster-session`
   - Accepts optional JSON: `{"channel_type": "webrtc"}` (defaulting to `"webrtc"`).
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
   - Deterministically destroys active WebRTC sessions and releases local resources.

---

## 4. Fake Vendor Harness, Retries & Error Handling

Local fake-vendor tests assert robust network behavior without live vendor dependencies:
- **Bounded Retry**: Exactly one retry attempt (maximum 2 attempts total) allowed only for transient upstream rate-limiting (`429`) or concurrency conflict (`409`).
- **No Retry on Client / Server Errors**: Errors such as `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, or `500 Internal Server Error` must fail immediately with no retry attempts.
- **Single-Flight Duplicate Rejection**: If a connection attempt is already in flight for a rehearsal session, concurrent requests must return `409 Conflict`.
- **Deterministic Cleanup**: On connection failure or session end, active WebRTC allocations must be cleaned up without leaking memory or file descriptors.

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
- A separate immutable test module (`test_s3_req7_live_gate.py`) guards live vendor calls.
- **Prerequisites**: `SAH_NAPSTER_LIVE=1`, `NAPSTER_API_KEY`, and `NAPSTER_AGENT_ID`.
- **Gate Absent**: Automatically skips with an explicit non-certifying skip message, exiting 0 with zero vendor calls.
- **Gate Open**: Drives the real app and browser, validating full SDK lifecycle (`readyVideo`, `onAvatarReady(true)`), verifying live mounted `<video>` and `<audio>` tracks, and asserting that a mere HTTP 200/token cannot certify.
- **Non-Certifying Mock Boundary**: Mock vendor success or offline test runs are explicitly declared insufficient for Stage 3 certification.

---

## 8. Real Evidence Schema & Redaction

Every Stage 3 evidence record must adhere to the following schema:
- `start_time_utc` and `end_time_utc`: Valid non-null ISO-8601 UTC strings. Synthetic timestamps (e.g. 1970/2000 epoch or future timestamps) are strictly rejected.
- `probe_correlation_hash`: 64-character lowercase hex SHA-256 string.
- `http_probe`: Dictionary with `host`, `path`, `method`, and `status_code`.
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
