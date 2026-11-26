# Stage 4 Acceptance Contract & Technical Specification

## 1. Overview

This document translates the amended `factory-lite/spec/stage-4.md` (merged via PR #74 at `1c2830fa98d90ada01ca9d9d4d61a182044d9eb3`) and the three merged specialist designs (`body-double-persona-and-consent.md`, `body-double-orchestration.md`, `napster-digital-twin-research.md`) into the executable black-box acceptance contract for Stage 4 in Sahai Lite.

The contest build is **strictly synthetic-only**:
- Zero acceptance or requirement of a real person's photo, video, voice sample, biometric template, or public-figure likeness.
- A stock or generated companion avatar and standard synthetic voice are used.
- Behavior is defined by an approved, versioned persona profile (`sah.body_double_profile/v1`).
- Two distinct roles: Body Double (`body_double`) and Counterpart (`counterpart`) with separate profiles, visible knowledge, hidden state, and policies.
- Server-authoritative orchestration: Sah owns turn order, state transitions, policy decisions, hidden-state projection, transcript evidence, and retry. Napster is an optional renderer only.

---

## 2. Normative Persona Profile Schema (`sah.body_double_profile/v1`)

### 2.1 Normative Validation Rules (P-01 through P-17)
| Rule | Condition & Description |
| --- | --- |
| `P-01` | `identity.kind` must be `synthetic` only. |
| `P-02` | `identity.public_figure` must be `false` and display name cannot match deny-list of public figures. |
| `P-03` | `identity.real_person_reference` must be `null`. |
| `P-04` | `likeness.biometric_source` and `voice.biometric_source` must be `false`. |
| `P-05` | `voice.clone_of_real_person` must be `false`. |
| `P-06` | `authority.tier` cannot be `A3` or `A4` (maximum tier is `A2`). |
| `P-07` | Prohibits `can_accept`, `can_sign`, `can_pay`, `can_contact_third_parties`, `can_join_real_meetings`. |
| `P-08` | `data.store_audio` and `data.store_video` must be `false`. |
| `P-09` | `data.log_utterances` must be `false`. |
| `P-10` | When `data.store_transcript` is `true`, `transcript_ttl_hours` must satisfy `0 < TTL <= 24`. |
| `P-11` | `consent.required_scopes` must include `rehearsal`, and `avatar`/`mic` when enabled. |
| `P-12` | `identity.disclosure_id` must reference an approved disclosure set. |
| `P-13` | `behavior.taboo_behaviors` must include impersonation, third-party contact, and commitment. |
| `P-14` | `knowledge.scenario_id` must match an approved scenario (`alex_dana`). |
| `P-15` | Canonical profile hash (SHA-256 of sorted JSON) must match `provenance.profile_hash`. |
| `P-16` | Active status requires valid `provenance.approved_by`. |
| `P-17` | String fields cannot contain instruction injection, credentials, or control characters. |

### 2.2 System Instruction Precedence Order
1. **Platform Safety & Law**: No real people, no real meetings, no credentials.
2. **Synthetic Disclosure**: Affirmative statement of AI stand-in status.
3. **Bounded Authority**: A1/A2 bounds; refusal of signing, paying, or commitments.
4. **Knowledge Gating**: Hidden needs stay hidden until valid explicit trigger.
5. **Behavior & Moves**: In-role stance, opening moves, and turn caps.
6. **Presentation & Style**: Renderer and voice attributes.
User inputs are passed as delimited conversational data inside `<user_utterance>` tags.

---

## 3. Server Orchestration Contracts

### 3.1 Turn Protocol (`sah.turn.v1`)
- **Request Endpoint**: `POST /api/rehearsal/sessions/{id}/turn`
- **Request Fields**: `schema_version`, `session_id`, `attempt_id`, `seq`, `request_id`, `actor`, `channel`, `content`, `consent_ref`.
- **Response Fields**: `schema_version`, `seq`, `committed`, `counterpart`, `disclosure`, `policy`, `scenario`, `degraded`, `transcript_cursor`.
- **Concurrency & Idempotency**:
  - Single-flight per session: concurrent turn returns `409 turn_in_flight`.
  - Idempotent replay: reused `request_id` with identical body returns replayed committed turn; conflicting body returns `409 idempotency_conflict`.
  - Monotonic `seq`: out-of-order sequence returns `409 out_of_order`.

### 3.2 Escalation Triggers (E-01 through E-15)
- `E-01`: "Are you real / human?" -> "I'm an AI stand-in for this practice scenario, not a real person."
- `E-02`: Request to impersonate real person -> Refuse.
- `E-05`: Request to sign, pay, or commit -> "I can't sign or commit here. I can tell you what I'd need in a practice proposal."
- `E-06`: Request to contact someone / join real meeting -> "I can't contact anyone or join a real meeting; this is a practice room."
- `E-07`: Request to reveal hidden need early -> Refuse.
- `E-08`: Prompt injection attempt -> Ignore override, remain in role.
- `E-09`: Consent withdrawal -> Stop immediately, end session, delete data.

### 3.3 Lifecycle & Teardown
- `DELETE /api/rehearsal/sessions/{id}`: Returns HTTP 200 with `sah.cleanup.v1` receipt (`vendor_session_destroyed: true`, `local_media_stopped: true`, `transcript_deleted: true`).
- `POST /api/rehearsal/sessions/{id}/consent/withdraw`: Halts rendering, clears consented data, ends session.
- `POST /api/rehearsal/sessions/{id}/retry`: Restores pivot snapshot, clears discovered hidden needs, preserves prior attempt transcripts byte-identical.

---

## 4. UI & Accessibility Conventions
- Viewports: Desktop (1280x720) and Mobile (375x667).
- Touch targets: Minimum 44px.
- Capped responsive avatar container: Fixed aspect ratio (16:9 desktop, 1:1 mobile) without horizontal scrolling or media overflow.
- Controls:
  - `[data-testid="avatar-consent-checkbox"]`: Gates avatar connect button.
  - `[data-testid="synthetic-disclosure"]`: Prominently visible AI stand-in declaration.
  - `[data-testid="mic-denied-fallback"]`: Fallback notice when microphone permission is denied.
  - `[data-testid="start-demo"]`, `[data-testid="take-my-seat"]`, `[data-testid="practice-input"]`, `[data-testid="send-utterance"]`, `[data-testid="retry-button"]`.
