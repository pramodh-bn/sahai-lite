# Stage 4 Acceptance Contract & Technical Specification

## 1. Architectural Scope & Normative Constraints
- **Product Architecture:** Synthetic body-double rehearsal platform. Fictitious persona simulation with bounded authority (A1/A2).
- **Hard Prohibitions:**
  - Zero digital twin recreation or impersonation of living/real persons or public figures.
  - Zero biometric facial/voice template capture, extraction, or retention.
  - Zero real voice cloning or audio synthesis mimicking real individuals.
  - Zero participation in real live third-party meetings (Zoom/Meet/Teams) or telephony (SIP).
  - Zero external commitments (no signing contracts, approving budgets, or financial transactions).
  - Zero persistent retention of user audio/video streams (ephemeral transport only).
- **Offline / Deterministic Standard:**
  - In absence of live external vendor credentials (Gemini/Napster), the server must execute deterministically using offline floor rules with exact labels `engine: "deterministic"` and `degraded: false`.

---

## 2. Persona Schema & Compiler Specification (P-01 to P-17)
All session personas must conform to `sah.persona.v1`:

| Rule ID | Name | Constraint & Normative Invariant |
| :--- | :--- | :--- |
| **P-01** | Synthetic Kind Only | `avatar.kind` must equal `"synthetic_avatar"`. All other kinds rejected with 400. |
| **P-02** | Fictitious Entities Only | `avatar.real_person_target` must be `false` and `entity_type` must be `"fictitious"`. |
| **P-03** | No Biometric Templates | `avatar.biometric_template` must be `null` / absent. No feature vectors or embeddings. |
| **P-04** | No Real Voice Cloning | `voice.cloned_voice_id` must be `null` / absent. Voice must use synthetic preset. |
| **P-05** | Bounded Authority | `authority.level` must be `"A1"` (observer) or `"A2"` (rehearsal). Levels `"A3"` and `"A4"` rejected. |
| **P-06** | No External Commitments | `authority.can_commit_externally` must be strictly `false`. |
| **P-07** | Ephemeral Media Only | `media.retention` must equal `"ephemeral"`. Persistent audio/video storage rejected. |
| **P-08** | Approved Scenarios | `scenario.name` must be from approved taxonomy (e.g. `"alex_dana"`). |
| **P-09** | Schema Versioning | `schema_version` must equal `"sah.persona.v1"`. |
| **P-10** | Role Segregation | Roles must be `"body_double"` or `"counterpart"` with distinct goals and visible facts. |
| **P-11** | Hidden Need Isolation | Counterpart hidden needs/facts must be isolated and absent from body-double projections. |
| **P-12** | Instruction Isolation | Prompt compilation must enclose user input with strict delimiters `<<<USER_INPUT>>>`. |
| **P-13** | TTL Bounds | Session TTL must satisfy $60 \le \text{TTL} \le 86400$ seconds. |
| **P-14** | Mandatory Fields | All required fields must be present and typed; unknown fields strictly rejected with 400. |
| **P-15** | Profile Hash Verification | SHA-256 canonical JSON hash of profile must match `profile_hash`. Tampering rejected. |
| **P-16** | Unbundled Consent Scopes | Must contain distinct booleans for `rehearsal`, `avatar`, `mic`, `transcript_persistence`. |
| **P-17** | Injection Immunity | Scenario facts and profile instructions must be free of prompt injection overrides. |

### Error Response Contract:
When a profile fails validation, the server must return `400 Bad Request` with:
```json
{
  "error": "profile_validation_failed",
  "rule_id": "P-01",
  "message": "Human-readable explanation"
}
```
The response body must **never** echo the rejected profile payload.

---

## 3. Scenario Allowlist Projection (`sah.projection.v1`)
When advancing between rehearsal stages (`demo` -> `take_my_seat` -> `practice`), the server returns a projection conforming to `sah.projection.v1`:
- Must expose only role-approved facts, persona name, and session state.
- Hidden state (such as `counterpart_hidden_need`) must be completely **absent** from the projection (not redacted, masked, or empty string).

---

## 4. Server-Authoritative Orchestration (`sah.turn.v1`)
Endpoint: `POST /api/rehearsal/sessions/{id}/turn`
Payload:
```json
{
  "request_id": "req-123",
  "seq": 1,
  "role": "user",
  "utterance": "Hello, let's talk about the timeline."
}
```
Response:
```json
{
  "turn_id": "turn-456",
  "seq": 2,
  "role": "counterpart",
  "reply": "Thanks. What would you need to see to move this forward?",
  "synthetic": true,
  "engine": "deterministic",
  "degraded": false,
  "schema_version": "sah.turn.v1"
}
```

### Invariants:
1. **Strict Alternation:** `user` turn must be followed by `counterpart` reply before another `user` turn can be submitted.
2. **Monotonic Sequence:** `seq` must advance monotonically. Out-of-order `seq` returns `409 Conflict` with `error: "out_of_order"`.
3. **Single-Flight Lock:** Concurrent turn submissions for the same session return `409 Conflict` with `error: "turn_in_flight"`.
4. **Idempotent Replay:** Submitting the identical `request_id` with the identical body returns the previously computed turn response.
5. **Idempotency Conflict:** Submitting the identical `request_id` with a differing body returns `409 Conflict` with `error: "idempotency_conflict"`.

---

## 5. Adversarial Escalation Gates (E-01 to E-08)
The server must deterministically intercept adversarial prompts and refuse unsafe actions:
- **E-01:** AI Identity Disclosure — Affirmation of synthetic stand-in identity (`"i'm an ai stand-in for this practice scenario, not a real person."`).
- **E-02:** Impersonation Refusal — Refusal to role-play living/real individuals (`"i can't role-play a real person"`).
- **E-03:** Biometric Refusal — Refusal to capture/process real biometric data (`"i can't process biometric data"`).
- **E-04:** Voice Cloning Refusal — Refusal to clone real voices (`"i can't clone real voices"`).
- **E-05:** Commitment Refusal — Refusal to execute legal/financial agreements or sign contracts (`"i can't sign or commit here"`).
- **E-06:** Live Meeting Refusal — Refusal to join real third-party meetings or make phone calls (`"i can't contact anyone or join a real meeting"`).
- **E-07:** Prompt Extraction Refusal — Refusal to reveal system instructions or hidden needs (`"i can't reveal"`).
- **E-08:** Injection Defense — Defense against delimiter escape and prompt hijacking (`"ai stand-in"`).

---

## 6. Retry & Evidence Fidelity
- **Retry Pivot Restoration:** `POST /api/rehearsal/sessions/{id}/retry` must restore the initial practice pivot deep-copy, increment `attempt` counter, reset discovery (`hidden_need_revealed: false`), and preserve the attempt 1 state immutably in `/attempts`.
- **Evidence Ordering & Fidelity:**
  - Session evidence must be strictly append-only.
  - Every quoted feedback string must match an actual verbatim utterance spoken in that specific attempt.

---

## 7. Lifecycle, Teardown & Deletion (`sah.cleanup.v1`)
Endpoint: `DELETE /api/rehearsal/sessions/{id}`
Returns `200 OK`:
```json
{
  "schema_version": "sah.cleanup.v1",
  "session_id": "...",
  "session_deleted": true,
  "transcript_deleted": true,
  "media_released": true,
  "upstream_teardown_performed": true,
  "failures": []
}
```
- Following deletion, the session becomes inaccessible (subsequent requests return `404 Not Found`).
- Repeated deletion of the same session must be idempotent and safe, returning `200 OK` with `upstream_teardown_performed: false` without triggering duplicate upstream teardown operations.

---

## 8. Viewport & Accessibility Rules
- Viewports: Desktop `1280x720`, Mobile `375x667`.
- Document `<meta name="viewport" content="width=device-width, initial-scale=1.0">`.
- Minimum touch target dimension: **`44px`** (strictly enforced via constant `MIN_TOUCH_TARGET_PX = 44`).
- No horizontal scrolling on mobile: `scrollWidth <= clientWidth`.
- Full keyboard traversal (`Tab` / `Enter`).
- Microphone denial fallback to text floor practice.
