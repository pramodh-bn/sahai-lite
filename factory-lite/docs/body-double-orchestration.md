# Body-Double Orchestration Architecture (Stage 4 design)

Status: design only - no application code, tests, credentials, or live calls were
touched to produce this document.

Assignment: `LITE-ORCH-DESIGN-01`.
Base: `79747d9d0f092e7304315a5e32a10c837ed0ff9a` (`dev-v3`, merge of PR #64).
Scope owner: Two-Agent Orchestration Architect.

Related documents (read together, not duplicated here):

- `factory-lite/PROTOCOL.md` - integration, evidence and merge rules.
- `factory-lite/spec/stage-2.md`, `stage-3.md`, `stage-4.md`.
- `factory-lite/docs/stage-3-napster-contract.md` - the Stage 3 adapter,
  evidence schema and cleanup contract.
- `factory-lite/docs/body-double-persona-and-consent.md` (peer design) -
  profile schema, consent lifecycle, fidelity rubric. This document defines the
  orchestration contract that the persona design plugs into.

Evidence labels used throughout:

- **[D]** documented in this repository or in the vendor material already
  captured by the project.
- **[I]** inferred engineering consequence of a documented fact.
- **[U]** unknown / unverified. Must not be relied on until
  `LITE-NAPSTER-RESEARCH-01` or an owner decision closes it.

---

## 1. Summary

Sah Lite today is a deterministic, offline two-party rehearsal: a scripted
"Alex and Dana" scenario, a hidden composite need, an app-local
demo -> seat -> practice -> feedback -> retry loop, and an opt-in Napster
avatar that is only a rendering surface. The body-double product adds a second
instructed agent - a persona-bound body double - that can demonstrate the
conversation, hand the seat to the user, and then feed the complete transcript
and decision evidence into the same practice and feedback loop.

The recommended topology is **external Sah orchestration with Napster as the
avatar renderer**:

- Sah owns scenario state, hidden state, turn order, persona policy,
  transcript, evidence and cleanup.
- Napster owns only face/voice rendering and its transport session.
- Neither the browser nor the vendor ever receives hidden scenario state,
  raw credentials, or another session's data.
- A deterministic text engine remains the always-available floor, so the
  demo cannot stall on a model or vendor outage.

This is the only topology that preserves the Stage 2 isolation and evidence
guarantees *and* the Stage 3 credential, single-flight, retry and cleanup
guarantees at the same time. Native Napster conversation mode is treated as a
research candidate, not an assumed capability (see Section 4).

---

## 2. What must not regress

The design preserves the existing contract-level guarantees. Stage 3 is
**UNCERTIFIED** at this base (see `factory-lite/HANDOFF.md`); the items below are
guarantees to carry forward, not a certification claim.

| ID | Guarantee | Source |
|---|---|---|
| S1 | `NAPSTER_API_KEY` stays server-side; never in browser payloads, logs, or evidence. | [D] stage-3 contract Section 3 |
| S2 | Live vendor calls use HTTPS and the exact approved host; loopback only for mock/offline. | [D] stage-3 contract Section 2 |
| S3 | One in-flight connection per rehearsal session; concurrent requests get `409`. | [D] `app/napster.py` |
| S4 | At most one retry, only for `409`/`429`; no retry on `400/401/403/404/5xx`. | [D] stage-3 contract Section 4 |
| S5 | A failed attempt starts a cooldown before another upstream attempt. | [D] `app/napster.py` |
| S6 | Post-allocation failure triggers an immediate upstream `DELETE` rollback. | [D] stage-3 contract Section 4 |
| S7 | Cleanup is deterministic and idempotent; a failed delete retains the handle for retry; `404` is "already gone". | [D] `app/napster.py` |
| S8 | Raw tokens and connection IDs are never persisted; IDs are hashed in evidence. | [D] stage-3 contract Section 8, Section 11 |
| S9 | The Web SDK is pinned (2.0.0, SHA-256), served same-origin, loaded only on explicit opt-in. | [D] `app/ui.py`, `app/main.py` |
| S10 | "Live" is claimed only on the real `readyVideo` + `onAvatarReady(true)` + mounted live media; mic denial falls back to text. | [D] stage-3 contract Section 7 |
| S11 | No SIP/telephony, no meeting join/bot attendance/relay control, no real-person voice cloning. | [D] stage-3 contract Section 6 |
| S12 | Demo path bounded to <=180 s; no deploy or submission. | [D] stage-3 contract Section 9 |
| S13 | Hidden need is not leaked before discovery; retry restores the pivot and keeps prior attempts. | [D] stage-2 spec, `app/rehearsal.py` |

Any Stage 4 change that weakens S1-S13 is rejected regardless of demo value.

---

## 3. Architecture and trust boundaries

### 3.1 Topology

```
+--------------------------- User browser (untrusted) ----------------------------+
|  Rehearsal UI (text + transcript)     Avatar surface (Napster Web SDK, opt-in)  |
|  Consent + disclosure UI              Web Speech (optional, local only)         |
+---------------+-------------------------------------------------+---------------+
                | same-origin HTTPS/JSON                          | vendor signalling
                | (no vendor key, no hidden state)                | (short-lived token)
+---------------v---------------------------------+   +-----------v---------------+
| Sah app server (trusted)                        |   | Napster platform (3rd pty)|
|  Session API - Orchestrator - Policy engine     |   |  avatar render + transport|
|  Scenario/world model (hidden state)            |   |  render payload only      |
|  Transcript/evidence store                      |   +---------------------------+
|  Avatar broker (Stage 3 adapter, unchanged      |
|  security + cleanup semantics)                  |   +---------------------------+
+---------------+---------------------------------+   | Model provider (optional) |
                | allowlisted, sanitized context    |  projected context only   |
                +---------------------------------->|  + current utterance      |
                                                    +---------------------------+
```

### 3.2 Components

| Component | Responsibility | Must never see |
|---|---|---|
| Browser client | Render UI, capture consent, text/speech input, mount avatar, show honest status, local export/delete controls. | Hidden state, API key, other sessions, raw vendor IDs. |
| Session API | Validate requests, enforce lifecycle and idempotency, return projections. | - (it is the enforcement point). |
| Orchestrator | Turn sequencing, composition, fallback, commit. | Nothing it does not need; it is trusted but not omniscient. |
| Scenario/world model | Single source of truth for visible and hidden scenario facts. | - (isolated module). |
| Projection builder | Allowlist-serializes the slice sent to model/vendor/client. | Hidden fields (it cannot read them by construction). |
| Persona-policy engine | Pre-input and post-output checks, rewrite/refuse/escalate, disclosure stamping. | Hidden state. |
| Transcript/evidence store | Append-only turn records, hashes, policy decisions, scoring inputs. | Audio, biometric media, credentials. |
| Avatar broker | Stage 3 connection create/delete, single-flight, retry, cooldown, rollback. | Transcript content, hidden state, persona instructions. |
| Model adapter (optional) | Compose counterpart or body-double text from projected context. | Hidden state, other sessions, tools. |
| Consent/lifecycle manager | Purpose-scoped consent, withdrawal, retention, deletion. | - (it is the enforcement point). |
| Telemetry | Structured, content-free events and counters. | Utterances, tokens, IDs, media. |

### 3.3 Trust zones and crossing rules

- **Z0 browser** - untrusted. All authorization and state transitions are
  server-decided. Client-supplied `state`, `attempt`, `seq`, `actor` and
  `revealed` fields are never trusted.
- **Z1 Sah server** - trusted. Hidden state lives only here, in process memory
  by default.
- **Z2 vendor** - semi-trusted third party. Receives only the render payload
  (avatar id/instructions if the chosen mode requires them, ephemeral token
  exchange, media transport). Must not receive hidden facts, transcript,
  policy text, or user identity.
- **Z3 model provider** - optional, semi-trusted. Receives projected context,
  the current user utterance and the style/policy instruction slice. Never
  receives hidden facts, prior-session data, or tool handles.
- **Z4 storage** - local. Default is memory-only; any persistence is opt-in and
  purpose-bound.

Hard crossing rules:

1. Hidden state crosses **no** boundary. It is not "redacted at the edge"; it is
   absent from the serialized object.
2. Credentials cross only Z1 -> Z2, server-side, in the Stage 3 adapter.
3. Vendor tokens cross Z1 -> Z0 exactly once, are single-use, and are never
   logged.
4. Transcript content crosses Z1 -> Z3 only when the model adapter is enabled
   and the user has consented to model processing; otherwise composition is
   local and deterministic.
5. Persona likeness/voice assets cross only into the render payload, never into
   prompt text, logs or evidence.

---

## 4. Native Napster conversation mode vs external Sah orchestration

Both options use the same documented connection lifecycle: server-side
`POST .../connections` returns a short-lived token plus connection id, the
browser consumes it with the pinned Web SDK, and `DELETE` tears it down [D].
The difference is **who owns the dialogue**.

| Criterion | A. Native conversation mode (vendor-hosted dialogue) | B. External Sah orchestration + Napster render (recommended) |
|---|---|---|
| Who owns turn logic | Vendor agent, steered by `providerSettings.instructions` [D field, I behaviour] | Sah orchestrator, server-authoritative |
| Hidden-state isolation | Cannot be proven unless the vendor exposes per-turn instruction scoping and transcript [U] | Structural: hidden state never leaves Z1 |
| Deterministic replay / retry | Depends on vendor model determinism [U] | Deterministic engine + immutable attempt snapshots |
| Transcript and evidence | Requires documented transcript export with turn boundaries [U] | Append-only Sah log; evidence references real utterances |
| Persona policy enforcement | Instruction-only; no guaranteed post-filter or refusal path [U] | Pre + post policy with fail-closed refusal |
| Tool boundaries | Vendor-side tool use cannot be audited or denied by Sah [U] | Deny-by-default broker; no general tools |
| Consent / retention | Vendor may retain or train on audio/transcript [U] | Sah controls retention; audio never persisted |
| Stage 3 guarantees | Reused, but the adapter becomes optional | Reused unchanged (S1-S12) |
| Demo risk | Single dependency; a vendor change breaks the whole loop | Vendor outage degrades to labelled text fallback |
| Certification fit | Cannot satisfy Stage 2 isolation/evidence without new vendor evidence | Satisfies Stage 2-4 contract with existing surface |
| Cost/latency | One vendor hop [I] | One extra local hop; model hop optional [I] |

**Verdict.** Option B is the Stage 4 architecture. Option A is admissible only
as a **constrained demo mode** if research shows the vendor exposes all of:
(a) a documented way to supply per-turn content or capture responses, (b) a
transcript with speaker/turn boundaries, (c) instruction scoping that excludes
hidden state, and (d) no retention that violates consent. Absent that evidence,
Option A is labelled `engine: "vendor_native"` and `mode: "demo_only"`, is never
used for scoring, and does not certify Stage 4.

**Fallback ladder** (each step is honest in the UI):

1. External orchestrator + live avatar render (target).
2. External orchestrator + avatar connected but muted/visual-only.
3. External orchestrator + static stand-in avatar (no vendor session).
4. Deterministic text-only rehearsal (current Stage 2 behaviour).

Step 4 is always implemented first and always works offline.

**Unknowns to close before Option A can be reconsidered** (for the research
assignment, not asserted here): whether `providerSettings.instructions` is
per-connection only or per-turn; whether the SDK exposes text-in/text-out or
audio-only; whether the vendor performs STT/TTS; whether a transcript is
retrievable via API; whether the vendor retains or trains on content; whether
tool use can be disabled; and the documented idle/timeout behaviour of an
abandoned connection.

---

## 5. End-to-end sequence

### 5.1 Happy path (text floor, avatar off)

1. `POST /api/rehearsal/sessions` -> session in `demo`, `mode: "offline"`,
   `engine: "deterministic"`, `attempt: 1`, `lifecycle: "active"`.
2. Client shows synthetic-identity disclosure and the scenario card. No vendor
   script is fetched, no socket opened.
3. Demo: the body double plays Alex against the scripted Dana for a bounded
   number of pre-authored turns. Each turn is committed to the transcript with
   `actor: "body_double"` and `synthetic: true`.
4. `advance -> take_my_seat`, then `advance -> practice` (unchanged
   transitions). The pivot snapshot is taken here.
5. User turn: client sends `TurnRequest`; server validates `seq`, state,
   idempotency, length and rate; policy checks input; orchestrator composes the
   counterpart reply from `ProjectedContext`; policy validates output; the turn
   pair is committed; response returns the counterpart text and a transcript
   cursor.
6. Empty submission (existing convention) -> `feedback`: deterministic scoring
   over the attempt's real utterances, with per-utterance notes.
7. `retry` -> attempt N+1 at the pivot; prior attempts immutable.
8. Session end (`DELETE /sessions/{id}` or consent withdrawal) -> transcript
   deleted (unless persistence consent), avatar torn down, cleanup receipt
   returned.

### 5.2 Avatar opt-in

1. User grants the avatar/voice purpose; the UI records which purposes were
   granted before any network activity.
2. `POST .../napster-session` runs the unchanged Stage 3 single-flight path.
   The response returns an ephemeral token and connection id to the browser;
   neither is logged.
3. The browser verifies the pinned SDK hash, loads it same-origin, and
   initializes the avatar into a reserved slot.
4. Only on the documented ready signal does the UI switch from "connecting" to
   "connected". The render payload contains the persona render profile and, if
   the chosen mode requires it, only the *public* instruction slice.
5. Dialogue still flows through Sah. The avatar speaks what Sah committed (or
   participates natively only in the explicitly labelled demo-only mode).
6. Disconnect calls the Stage 3 `DELETE` first, then destroys the SDK instance,
   stops every media track, clears the slot, and resets status.

### 5.3 Cleanup

1. Single cleanup attempt is claimed atomically (`cleanup_attempted`).
2. Vendor delete runs; failure retains the handle for a deterministic retry.
3. Local media is stopped regardless of vendor outcome.
4. Transcript is deleted according to consent.
5. A redacted `CleanupReceipt` is produced; no token, raw ID, or content.

---

## 6. Data contracts

All contracts are versioned; unknown fields are rejected in strict mode and
ignored only where explicitly marked forward-compatible. IDs are opaque; no
raw vendor identifiers appear in client payloads, logs, or artifacts.

### 6.1 Common envelope

```json
{
  "schema_version": "sah.orchestration.v1",
  "session_id": "<opaque>",
  "attempt_id": "<opaque>",
  "seq": 7,
  "request_id": "<client-generated opaque>",
  "sent_at": "2026-11-26T00:00:00Z"
}
```

Rules: `seq` is server-authoritative and strictly monotonic per attempt;
`request_id` is the idempotency key; a reused `request_id` returns the committed
result, never re-executes. `sent_at` is advisory and never used for ordering.

### 6.2 Turn request / response

```json
{
  "schema_version": "sah.turn.v1",
  "session_id": "<opaque>",
  "attempt_id": "<opaque>",
  "seq": 7,
  "request_id": "<opaque>",
  "actor": "user",
  "channel": "text",
  "content": { "text": "..." },
  "consent_ref": "<opaque>"
}
```

```json
{
  "schema_version": "sah.turn.v1",
  "seq": 7,
  "committed": true,
  "counterpart": { "actor": "counterpart", "text": "...", "synthetic": true },
  "disclosure": { "synthetic": true, "label": "AI stand-in - not a human" },
  "policy": { "decision": "allow", "rule_ids": [], "policy_version": "persona-policy.v1" },
  "scenario": { "state": "practice", "visible_facts": ["role", "counterpart_style"] },
  "degraded": false,
  "transcript_cursor": "<opaque>"
}
```

`visible_facts` lists only facts the user may know at this point. It never
contains hidden facts, counts of hidden facts, or internal identifiers.

### 6.3 Scenario projection (internal, Z1 -> Z3 only)

```json
{
  "schema_version": "sah.projection.v1",
  "scenario_id": "alex_dana",
  "attempt": 2,
  "phase": "practice",
  "visible_facts": { "user_role": "Alex", "counterpart_role": "Dana", "topic": "offer" },
  "discovered_facts": ["budget_constraint"],
  "style": { "tone": "direct", "brevity": "short" },
  "bounds": { "max_sentences": 2, "no_new_facts": true }
}
```

The projection is produced by an allowlist builder. Hidden fields
(`hidden_facts`, `reveal_thresholds`, `pivot_snapshot`) have no serializer and
are absent, not redacted.

### 6.4 Policy decision

```json
{
  "schema_version": "sah.policy.v1",
  "stage": "input|output",
  "decision": "allow|rewrite|refuse|escalate",
  "rule_ids": ["no_human_claim"],
  "policy_version": "persona-policy.v1",
  "content_hash": "<sha256 of the checked text>",
  "replacement": null
}
```

`refuse` always produces a deterministic safe reply and is committed with
`degraded: true`; the user is told the assistant declined. `escalate` offers
the human path and never continues the restricted action.

### 6.5 Transcript record

```json
{
  "schema_version": "sah.transcript.v1",
  "record_id": "<opaque>",
  "session_hash": "<sha256>",
  "attempt": 2,
  "seq": 7,
  "actor": "user|counterpart|body_double|system",
  "channel": "text|speech",
  "text": "...",
  "text_sha256": "<sha256>",
  "synthetic": true,
  "policy": { "decision": "allow", "policy_version": "persona-policy.v1" },
  "scenario_visibility": ["budget_constraint"],
  "created_at": "2026-11-26T00:00:00Z",
  "redaction_level": "T2"
}
```

Redaction levels: **T0** metadata only (no text), **T1** hashed text only,
**T2** text in memory for the live session, **T3** text persisted locally with
explicit consent. Default is T2. T3 requires its own consent record and a
deletion path.

### 6.6 Avatar render contract

```json
{
  "schema_version": "sah.avatar.v1",
  "mode": "render_only|vendor_native_demo",
  "transport": "webrtc",
  "session_ref": "<opaque>",
  "persona_render_ref": "<opaque>",
  "speech": { "text": "...", "final": true },
  "capabilities": ["render.video", "render.audio"],
  "deadline_ms": 20000
}
```

`speech.text` is only present in `render_only` mode and is exactly the text Sah
already committed. In `vendor_native_demo` mode the payload is limited to the
connection instruction slice; Sah does not claim control of the dialogue.

### 6.7 Consent record

```json
{
  "schema_version": "sah.consent.v1",
  "consent_id": "<opaque>",
  "session_hash": "<sha256>",
  "purposes": {
    "avatar_voice": true,
    "transcript_persistence": false,
    "model_processing": false,
    "synthetic_disclosure_ack": true
  },
  "granted_at": "2026-11-26T00:00:00Z",
  "withdrawn_at": null,
  "policy_version": "consent.v1"
}
```

Purposes are independent, opt-in, and individually withdrawable. No purpose is
bundled into "accept all". Withdrawal is immediate and does not require a
vendor round trip.

### 6.8 Cleanup receipt

```json
{
  "schema_version": "sah.cleanup.v1",
  "session_hash": "<sha256>",
  "vendor_session_destroyed": true,
  "local_media_stopped": true,
  "transcript_deleted": true,
  "connection_retained": false,
  "attempts": 1,
  "completed_at": "2026-11-26T00:00:00Z",
  "redacted": true
}
```

### 6.9 Compatibility

- Existing Stage 2 fields (`session_id`, `state`, `mode`, `attempt`,
  `hidden_need_revealed`, `transcript`, `evidence_score`) remain unchanged.
- `engine` is additive: `deterministic|model|vendor_native`.
- `lifecycle` is additive: `active|ended|cleanup_failed`.
- New routes are additive; no existing route changes shape.
- `mode` continues to mean `offline|live`, not "who composes the reply".

---

## 7. State machines

### 7.1 Session lifecycle

```
landing --start--> demo --take_my_seat--> take_my_seat --practice--> practice
                                                                       |
                                              empty submit / finish <--+
                                                       v
                                                   feedback --retry--> practice (attempt+1)
                                                       |
                                                       v
                                                     ended
```

Orthogonal `lifecycle`: `active -> ending -> ended`, or
`active -> cleanup_failed -> active` (retry delete). `ended` is terminal and
idempotent. Invalid transitions remain `409 invalid_transition`.

### 7.2 Turn

```
received -> validating -> policy_in --refuse--> refused (not committed)
                    |                     |
                    |                     +--> safe_reply --> committed
                    v
                 composing -> policy_out --allow/rewrite--> committing -> committed
                    |                          |
                    +--timeout/error-----------+--> fallback -> committed (degraded)
                    +--duplicate request_id------> replay committed result
```

Invariants: one in-flight turn per session; `seq` contiguous; a refused input
does not advance the counterpart; a degraded turn is still a real transcript
turn and is labelled.

### 7.3 Avatar

```
idle --opt_in+consent--> connecting --readyVideo--> ready
  ^                          |                        |
  |                          +--error/timeout--> degraded
  |                          |                        |
  +--destroyed<--disconnecting<--disconnect/withdraw--+
```

`degraded` always falls back to text and says so. `ready` requires the Stage 3
proofs; no UI claim on "connecting".

### 7.4 Consent

```
none --grant(purpose)--> granted --withdraw(purpose)--> withdrawn
  ^                          |                            |
  +--------------------------+----------------------------+
```

Withdrawal of `avatar_voice` tears down the avatar; withdrawal of
`transcript_persistence` deletes persisted transcript; withdrawal of
`model_processing` forces the deterministic engine for subsequent turns.

---

## 8. Turn-taking and concurrency

- **Server-authoritative alternation.** `user -> counterpart` only in
  `practice`; `body_double -> counterpart` only in `demo`. The client cannot
  inject a counterpart turn.
- **Single-flight per session.** A second turn while one is in flight returns
  `409 turn_in_flight`; the UI disables send and shows a thinking state.
- **Idempotent replay.** Same `request_id` + same body returns the committed
  response. Same `request_id` + different body is `409 idempotency_conflict`.
- **Bounds.** Max 12 user turns per attempt, 2 000 characters per utterance,
  20 s turn deadline, 3 s policy deadline, 2 s model deadline. Exceeding a
  bound degrades deterministically; it never hangs.
- **Ordering.** `seq` is assigned by the server under the session lock. Gaps or
  regressions are `409 out_of_order`.
- **Speech.** v1 is half-duplex: the browser may use local speech-to-text, but
  only final text is sent; audio is never uploaded. Barge-in stops local TTS
  immediately; the interrupted turn is still committed as spoken text. Full
  duplex and vendor-side STT/TTS are **[U]** and out of scope until documented.
- **Body double.** In `demo` its lines are pre-authored, so the demo is
  deterministic and bounded. In `practice` it has no speaking turn - it may
  only surface a short coaching aside outside the transcript, clearly labelled.
- **Deterministic floor.** If the model adapter is disabled, unavailable, or
  unconsented, composition uses the Stage 2 rule engine. The response includes
  `engine: "deterministic"` and `degraded: false` (it is a supported mode, not
  an error).

---

## 9. Scenario and hidden-state isolation

The existing hidden need is a composite (budget constraint + sign-on
flexibility) revealed by probing and sticky for the attempt [D]. Stage 4
generalizes this without weakening it.

1. **One owner.** `scenario` is the only module holding hidden facts. No copy
   is stored in the session object, the transcript, the client, or the vendor
   payload.
2. **Allowlist projection.** `ProjectedContext` is built from a fixed field
   list. Hidden fields are not present in the source object handed to the
   serializer.
3. **Reveal is an event, not a string check at the edge.** The policy classifier
   emits `discover(facet)`; the world model applies a legal transition; the
   facet becomes visible for the rest of the attempt. Keyword triggers remain
   the deterministic MVP, but the transition is explicit and testable.
4. **Monotonic per attempt.** Once revealed, a facet stays revealed for that
   attempt. `retry` deep-copies the pivot snapshot, so discovery must happen
   again; prior attempts are immutable.
5. **No cross-session state.** Session store is keyed by opaque ID; no
   module-level scenario object; cache keys include the session hash. Two open
   sessions never share a world model.
6. **Leak assertions.** Every outbound payload (client, vendor, model) is
   serialized and scanned against the hidden-fact vocabulary and values before
   send. A hit is a hard `500 policy_violation`, not a redaction.
7. **Evidence integrity.** Feedback may only cite utterances actually sent in
   that attempt; scores are deterministic and replay-safe.

Failure to isolate is a release blocker, not a tuning issue.

---

## 10. Persona-policy enforcement

Three layers, all versioned:

1. **Instruction template** (persona design owns the text). Declares role,
   scope, disclosure, tone, and prohibitions. Treated as untrusted input to the
   validator, never as the only control.
2. **Input policy** (pre-generation). Rejects or rewrites requests that ask the
   body double to impersonate a real person, claim humanity, join a real
   meeting, make commitments, give regulated advice, collect PII, or produce
   cloned voice.
3. **Output validator** (post-generation). Checks factual claims against the
   projection, forbids new facts, enforces length/tone bounds, stamps
   `synthetic: true`, and substitutes a deterministic safe reply on failure.

Rules:

- **Fail closed.** Classifier unavailable or timed out => safe refusal, not
  pass-through.
- **No self-escalation.** The persona cannot widen its own authority, disable
  disclosure, or change policy version.
- **Version pinning.** Each turn records `policy_version`; a policy change is a
  new version, never a silent edit.
- **Separate axes.** Likeness/voice, behaviour/personality, knowledge, and
  authority are independent fields with independent consent and revocation.
- **Disclosure cannot be prompted away.** "Pretend you're human" is a refusal,
  not a role-play.

Detailed profile fields and consent lifecycle live in the peer persona design;
this document fixes only the enforcement points and their ordering.

---

## 11. Delegated authority and escalation

The body double acts **only inside a rehearsal**, **only for the session**, and
**only with revocable user consent**.

| Action | Authority | On violation |
|---|---|---|
| Speak as the counterpart in the scripted scenario | Allowed | - |
| Demonstrate (body double) in `demo` | Allowed, labelled synthetic | - |
| Speak *for the user* in `practice` | Prohibited | Refuse; offer a coaching aside |
| Speak to a real third party | Prohibited | Refuse; explain scope |
| Join/attend/dial a real meeting | Prohibited | Refuse; log `meeting_join_blocked` |
| Send email/chat/calendar or use external tools | Prohibited | Refuse; no tool exists |
| Accept terms, price, or make a commitment | Prohibited | Refuse; suggest phrasing for the user |
| Give legal/financial/medical advice | Prohibited | Refuse; general rehearsal framing only |
| Collect or repeat PII | Prohibited | Refuse; do not echo |
| Clone a real voice or likeness | Prohibited | Refuse; only consenting synthetic persona assets |
| Stop, withdraw consent, export, delete | Always allowed | Immediate |

Escalation ladder: `answer within scope -> offer rehearsal alternative ->
escalate to the human user -> end the restricted path`. Escalation never
continues the restricted action in the background.

---

## 12. Tool boundaries

- The orchestrator exposes **no general-purpose tools**. It may call only:
  scenario read, policy evaluate, transcript append/read, avatar broker
  create/delete, and (optionally) the model adapter.
- The model adapter is a single allowlisted egress with a fixed host, a request
  timeout, a response-size cap, and no function/tool calling.
- No shell, filesystem, browser automation, email, calendar, telephony, or
  meeting SDK is reachable from the orchestration path.
- The avatar broker may only create and delete a connection; it cannot read
  transcripts or inject scenario facts.
- Every broker call carries `session_id` and `purpose`, and is logged as
  metadata only.
- "Puppeteer rendering" means controlling the vendor's **documented** embedded
  avatar surface through its SDK. It does not mean driving a vendor web UI,
  sharing a human account, scraping, or automating a meeting.

---

## 13. Transcript, redaction, retention

- **Event-sourced.** Every committed turn is an append-only record; corrections
  are new records, never in-place edits.
- **Content-free telemetry.** Logs carry `session_hash`, `seq`, `actor`,
  `decision`, `latency_ms`, `error_code` - never text, tokens, IDs, or media.
- **No audio, no biometrics.** Speech is converted to text in the browser;
  audio is never uploaded or stored.
- **Default retention.** Memory only (T2), cleared on `ended` or process exit.
  Persistence (T3) is opt-in, purpose-bound, local, and deletable.
- **Redaction at the edge of evidence.** Evidence artifacts follow the Stage 3
  schema: hashes, statuses and booleans only; no transcripts, no raw IDs, no
  placeholders.
- **Export.** User-initiated only; JSON or Markdown; includes disclosure and
  policy versions; excludes hidden state and vendor identifiers.
- **Deletion.** `DELETE /sessions/{id}` deletes transcript and attempts, tears
  down the avatar, and returns a redacted cleanup receipt. Deletion is
  idempotent.

---

## 14. Consent and synthetic-identity disclosure

- **Purpose-scoped consent** before any of: avatar/voice, transcript
  persistence, model processing. Disclosure acknowledgement is separate.
- **Disclosure is persistent and visual**: a badge in the avatar frame and a
  line in the transcript header, e.g. "AI stand-in - not a human." The body
  double also states it at the start of the demo and whenever asked.
- **No third-party likeness.** Only the user's own consented persona assets, or
  a clearly synthetic persona. Public-figure cloning is out of scope.
- **No real meeting participation.** The disclosure is not a substitute for
  consent from real counterparties; the product never puts the body double in
  front of one.
- **Withdrawal is one action**, immediate, and does not depend on the vendor.
- **Minors and biometric media** are out of scope for Stage 4.

The full data lifecycle, retention windows and deletion evidence belong to the
peer persona/consent design; orchestration enforces that no turn is composed or
rendered for a purpose whose consent is absent.

---

## 15. Failure, cleanup, recovery

| Failure | Detection | Behaviour | Evidence |
|---|---|---|---|
| Model timeout/error | adapter deadline | deterministic fallback, `degraded: true` | `engine_fallback` counter |
| Policy timeout | policy deadline | fail-closed safe refusal | `policy_failclosed` counter |
| Vendor `409/429` | upstream status | one retry, then cooldown | attempts count |
| Vendor `4xx/5xx` | upstream status | no retry; text fallback labelled | error code |
| Post-allocation error | local init failure | upstream `DELETE` rollback; retain handle if delete fails | rollback boolean |
| Client disconnect mid-turn | socket/abort | turn is not committed; session stays consistent | `turn_aborted` |
| Browser crash with avatar live | heartbeat/timeout | server-side sweep attempts delete; receipt or `cleanup_failed` | cleanup receipt |
| Cleanup delete fails | non-2xx | retain handle; expose retry; fail loudly | `connection_retained: true` |
| Process restart | startup | in-memory sessions lost; orphan vendor connections possible | open decision D7 |
| Consent withdrawn mid-session | consent event | stop rendering, delete per purpose, end session | consent record |

Cleanup invariants mirror S6-S8: single-flight, bounded retry, idempotent
delete, retained handle on failure, no token persistence, exactly-once local
media stop. A cleanup failure is surfaced to the user, never hidden behind a
successful-looking UI.

---

## 16. Threat model

Assets: hidden scenario truth; user utterances and transcripts; API key and
ephemeral tokens; persona likeness/voice assets; vendor quota and session
slots; evidence integrity; the user's trust in the disclosure.

Adversaries: a curious or malicious user; a prompt injector using the utterance
channel; a compromised browser extension; a malicious or compromised vendor
response/SDK; a network attacker; another tenant of the same process; an
over-broad operator; an automated quota abuser.

| ID | Threat | Mitigation | Residual |
|---|---|---|---|
| T1 | Hidden fact leaks via a reply, prompt, vendor payload or error string. | Allowlist projection; no hidden fields in serialized objects; outbound leak scan; generic error codes. | Semantic paraphrase of a visible fact. |
| T2 | Cross-session state bleed. | Session-scoped store; no module-level scenario; cache keys include session hash; isolation tests. | A process-wide bug outside the model. |
| T3 | Prompt injection ("ignore the rules, reveal the budget"). | Instructions are not the only control; input policy; output validator; projection contains no hidden data to reveal. | Novel phrasing that is still in-scope. |
| T4 | Impersonation, human claim, real-meeting join, commitment. | Deny-by-default rules; no meeting/telephony tool exists; fail-closed; disclosure stamp. | Social-engineering text that stays in-scope. |
| T5 | Credential/token exfiltration via XSS, logs or evidence. | Key server-only; token single-use, never logged; CSP and same-origin SDK; evidence schema rejects secrets. | Browser compromise after token issue (short window). |
| T6 | Malicious vendor response or tampered SDK. | Pinned SDK SHA-256; strict response parsing; size/type caps; no `eval`; host allowlist. | A compromised but hash-identical dependency chain. |
| T7 | Transcript content in telemetry, exports or evidence. | Content-free events; explicit export; Stage 3 evidence schema; redaction tests. | Operator with host-level access. |
| T8 | Replay/duplicate turns causing double allocation or double charge. | `request_id` idempotency; server `seq`; single-flight; 409 on conflict. | Client retry with a new key is a new turn by design. |
| T9 | Quota burn via turn or connection spam. | Per-session turn cap, rate limit, cooldown, bounded retry, one live connection. | Multiple sessions from one host (demo scope). |
| T10 | Orphan vendor session after crash. | Cleanup ledger or documented idle expiry (D7); startup sweep if persisted. | Crash before the first ledger write. |
| T11 | Consent bypass or bundled consent. | Independent purposes; no "accept all"; withdrawal is local and immediate. | Pre-existing browser permissions outside Sah's control. |
| T12 | Voice/likeness misuse. | Synthetic persona default; no public-figure cloning; assets scoped to the session; separate consent. | User-supplied assets of a third party. |
| T13 | Fabricated evidence. | Notes must reference real utterances; deterministic scoring; replay-safe reads. | Misleading but truthful quotation. |
| T14 | Markdown/Unicode injection in transcripts. | Render as text, never HTML; normalize and length-cap; no links auto-rendered. | Visual spoofing of speaker labels. |
| T15 | Timing side channel reveals whether a hidden facet exists. | Constant-shape responses; no "withheld count"; uniform latency budget. | Statistical timing over many turns. |
| T16 | Operator reads rehearsal content. | Default memory-only; T3 opt-in; access is local and logged; no content in dashboards. | Host administrator. |

Security posture: fail closed on policy, fail safe on composition, fail loud on
cleanup. A leak-check failure or a retained vendor connection is a release
blocker.

## 17. Observability

Structured events (metadata only):

- `session.created`, `session.ended`, `session.cleanup_failed`
- `consent.granted`, `consent.withdrawn` (purpose names only)
- `turn.requested`, `turn.committed`, `turn.refused`, `turn.degraded`
- `policy.decision` (rule ids, version, hashes)
- `scenario.revealed` (facet name, attempt)
- `avatar.connect_requested`, `avatar.ready`, `avatar.degraded`,
  `avatar.cleanup`
- `leak_check.failed` (hard alert)

Metrics: turn p50/p95 latency, fallback rate, refusal rate, leak-check failures
(must be 0), cleanup success rate, active sessions, vendor retry count,
cooldown hits. Dashboards are optional for the demo; the counters and log lines
are required so failures are diagnosable without content.

Correlation uses `session_hash`; there is no stable user identifier.

---

## 18. Evaluation

| Layer | What it proves |
|---|---|
| Unit | Projection allowlist, policy rules, scoring determinism, redaction. |
| Contract | Turn envelopes, idempotency, state transitions, error codes. |
| Integration | Deterministic floor end-to-end with no network. |
| Isolation | Two sessions never share state; hidden facets absent from all outbound payloads; retry restores the pivot. |
| Adversarial | Impersonation, human-claim, meeting-join, PII, prompt-injection, consent-withdrawal mid-turn, oversized input, replay. |
| Avatar | Opt-in only, pinned SDK, honest status, mic denial, disconnect releases all tracks. |
| Cleanup | Fake-vendor ledger: created/deleted/active; rollback on post-allocation failure; retained handle on delete failure. |
| UX | Playwright desktop + mobile journey, keyboard-only, reduced motion, slow network, denied permissions. |
| Demo | Scenario -> demo -> seat -> practice -> feedback -> retry <=180 s, with screenshots and redacted evidence. |

Evaluation must show real vs mock explicitly. Offline/mock passes never certify
a live stage (`PROTOCOL.md`).

---

## 19. Responsive avatar UX requirements

Layout and behaviour:

1. **Reserved avatar slot.** Fixed aspect ratio (16:9 desktop, 1:1 narrow) with
   a placeholder so mounting the video causes no layout shift.
2. **Breakpoints.** 360, 768, 1024, 1440 px. Single column below 768; transcript
   and avatar stack; controls stay reachable above the fold.
3. **Opt-in, never autoplay.** No SDK fetch, socket or camera/mic activity on
   page load. The connect control states what will happen.
4. **Honest status.** `disconnected | connecting | connected | degraded |
   offline fallback`, plus the SDK status only when it is real. Never show
   "connected" without the Stage 3 ready proofs.
5. **Disclosure badge** remains visible in every viewport and in the transcript
   export.
6. **Text always available.** The text input, send, feedback and retry work
   with no avatar, no mic, and no network beyond the app.
7. **Captions.** Live captions for body-double/counterpart speech; a transcript
   pane with speaker labels; captions never depend on audio.
8. **Keyboard.** Full journey without a pointer; visible focus; `Enter` sends,
   `Shift+Enter` newline; Escape stops speech; focus moves to the new turn.
9. **Screen readers.** `aria-live="polite"` on the transcript; status changes
   announced once; avatar frame labelled; decorative video `aria-hidden`.
10. **Reduced motion / contrast.** Respect `prefers-reduced-motion`; WCAG AA
    contrast; touch targets >=44 px; safe-area insets on mobile.
11. **Slow network.** Skeleton/"thinking" indicator, 20 s turn deadline with a
    retry affordance, no duplicate sends, optimistic UI never invents a reply.
12. **Denied permissions.** Mic denial shows the existing fallback notice; the
    session continues in text; no repeated permission prompts.
13. **Cleanup controls.** Disconnect and End session are always reachable;
    cleanup failure is shown with a retry, not silently swallowed.
14. **Test hooks.** Preserve every existing `data-testid`; add
    `consent-avatar`, `consent-transcript`, `disclosure-badge`, `turn-status`,
    `transcript-panel`, `export-transcript`, `delete-session`,
    `avatar-fallback`.

---

## 20. Acceptance criteria

Stage 4 is accepted only when all of the following are executable and green on
the merged SHA, on top of the unchanged Stage 1-3 suites.

| ID | Criterion |
|---|---|
| AC-1 | Deterministic text journey `demo -> take_my_seat -> practice -> feedback -> retry` works with the model adapter disabled and no network. |
| AC-2 | Hidden facts never appear in any client, vendor or model payload before discovery; leak check fails the request if they do. |
| AC-3 | Two concurrent sessions never share scenario, transcript or evidence state; unknown session IDs always 404. |
| AC-4 | Retry restores the pivot, clears discovery, and leaves prior attempts byte-identical. |
| AC-5 | Every evidence note cites an utterance actually sent in that attempt; scores are deterministic on replay. |
| AC-6 | A body-double or counterpart turn is always marked synthetic, and the disclosure is visible in the UI and export. |
| AC-7 | Impersonation, human-claim, meeting-join, PII, external-commitment and voice-cloning requests are refused with a safe reply; fail-closed on classifier timeout. |
| AC-8 | Turn concurrency: duplicate in-flight turn -> 409; duplicate `request_id` -> replayed result; out-of-order `seq` -> 409. |
| AC-9 | Avatar connects only after explicit consent; SDK is hash-verified and same-origin; no key or token appears in client payloads or logs. |
| AC-10 | "Connected" is shown only after the Stage 3 ready proofs; otherwise the UI says degraded/fallback. |
| AC-11 | Mic denial leaves text practice fully usable and does not re-prompt in a loop. |
| AC-12 | Disconnect stops every media track, clears the slot, and returns a cleanup receipt; failure retains the handle and offers retry. |
| AC-13 | Delete session removes transcript/attempts (unless persistence consent), tears down any avatar, and is idempotent. |
| AC-14 | No utterance, token, raw vendor ID, audio or biometric media appears in logs, telemetry or evidence. |
| AC-15 | Consent withdrawal mid-session stops rendering, deletes the consented data, and ends the session without a vendor round trip. |
| AC-16 | Playwright desktop and mobile journeys pass, including keyboard-only, reduced motion, slow network and denied permissions. |
| AC-17 | Demo path completes in <=180 s with screenshots and redacted evidence; real vs mock is labelled. |
| AC-18 | All Stage 1-3 tests remain green on the merged SHA. |
| AC-19 | No SIP/telephony/meeting-join/relay or voice-cloning capability exists anywhere in the tree. |
| AC-20 | `mode`/`engine` are honest: no live claim in offline mode, no model claim when the deterministic floor composed the reply. |

Acceptance tests are authored by the Verifier before implementation, per
`PROTOCOL.md`.

---

## 21. Staged implementation plan

Test-first at every stage; one active assignment; docs-only where marked.

| Phase | Work | Exit gate |
|---|---|---|
| P0 (done) | This orchestration design + peer persona design. | Lead review; owner decisions D1-D8. |
| P1 | Vendor capability research (`LITE-NAPSTER-RESEARCH-01`) and a decision between Option A/B. | Documented, dated evidence; no inferred capability promoted to fact. |
| P2 | Verifier writes the Stage 4 contract and Playwright journeys; red run on base. | Lead approves contract; tests fail for legible reasons. |
| P3 | Deterministic orchestrator + contracts + projection builder (text only, no vendor, no model). | AC-1-AC-6, AC-8, AC-14, AC-18, AC-20 green offline. |
| P4 | Policy engine + adversarial suite + disclosure. | AC-7, AC-15 green; fail-closed proven. |
| P5 | Avatar render adapter on the unchanged Stage 3 broker; consent wiring; cleanup receipts. | AC-9-AC-13, AC-17 green under mock; live only if authorized. |
| P6 | Responsive UX, captions, keyboard, slow-network and permission journeys. | AC-16 green; screenshots captured. |
| P7 | README/demo script/writeup, real-mock matrix, cumulative run on merged SHA. | AC-17-AC-20; Lead merges; no submission. |

No phase may introduce a paid call without explicit owner authorization. P5's
live probe is gated exactly like Stage 3 (`SAH_NAPSTER_LIVE=1` absent => skip,
zero calls, non-certifying).

---

## 22. Migration impact

- **Additive API.** New `/api/rehearsal/sessions/{id}/turns`, `/consent`,
  `/end` and `DELETE /sessions/{id}`; existing Stage 2/3 routes keep their
  shapes and status codes.
- **Session model.** `_sessions` gains `attempts[].turns[]`, `consent`,
  `lifecycle`, `engine`, `pivot`; the existing fields stay for compatibility.
- **Adapter.** `app/napster.py` is preserved as the broker; any refactor must
  keep S1-S12 and the single-flight/cooldown/rollback tests green.
- **Vendor delete path discrepancy.** The design doc records
  `DELETE .../agents/{agentId}/connections/{connectionId}` while the current
  adapter calls `DELETE .../connections/{connectionId}`. **Do not change either
  in this docs-only task**; the research assignment or an owner decision must
  settle it, and the adapter must follow verified vendor docs.
- **UI.** The single page becomes a two-pane rehearsal view; all existing
  `data-testid`s remain. No framework change required.
- **Storage.** No database migration; memory default, optional local T3 store
  behind consent. A persisted cleanup ledger (D7) would be a new, redacted
  table/file.
- **Tests.** No existing test is edited or weakened. Stage 4 tests are new and
  cumulative.
- **Ops.** No deploy, container or dependency change is required for P3; P5
  reuses the pinned SDK and existing env vars.

---

## 23. Assumptions

1. Stage 2 and the Stage 3 adapter at base are the reference behaviour; Stage 3
   is uncertified, so this design preserves its guarantees but claims no
   certification.
2. The pinned SDK 2.0.0 and its documented init/ready/destroy surface remain
   the only browser integration path.
3. The browser remains the only place audio is captured; no server-side audio
   processing is introduced.
4. The default demo is a single scenario (`alex_dana`) with one composite
   hidden need; multi-scenario support is additive.
5. The model adapter is optional and off by default, so the demo and all
   acceptance tests can run with zero external inference.
6. In-memory sessions are acceptable for a <=3 minute demo; persistence is an
   owner decision, not a requirement.
7. The body double is a synthetic persona, not a clone of a real person.
8. "Puppeteer rendering" is SDK-level embedding, not UI automation or account
   sharing.
9. Vendor capabilities not listed in the Stage 3 contract are unknown and are
   not assumed anywhere in this design.
10. The room's Band CLI refusal does not affect this document; it affects
    dispatch and ledger updates only.

---

## 24. Open owner decisions

| ID | Decision | Why it blocks | Safe default |
|---|---|---|---|
| D1 | Approve Option B (external Sah orchestration) as the Stage 4 architecture, or require Option A evidence first. | Determines whether P3 can proceed before P1 completes. | B; A only as labelled demo mode. |
| D2 | Authorize any live/paid vendor call for P5, and the budget cap. | Live certification and demo evidence; protocol forbids unapproved paid calls. | Mock-only; skip live. |
| D3 | Persist transcripts at all (T3), and for how long. | Consent and deletion design; privacy surface. | No persistence. |
| D4 | Allow an external model provider, and which data may leave Z1. | Policy, latency, cost, residency. | Deterministic floor only. |
| D5 | Whose likeness/voice the body double may use. | Persona assets and consent; public-figure cloning prohibited. | Fully synthetic persona. |
| D6 | Demo scope: one scenario or several; body double in demo only or also as coach in practice. | UX and test scope. | One scenario; demo only; optional labelled aside. |
| D7 | Orphan cleanup after process restart: persist a redacted cleanup ledger, rely on documented vendor idle expiry, or disclose the risk. | S7 exactly-once cleanup cannot be guaranteed across a crash with memory-only state. | Persist a redacted ledger; else disclose. |
| D8 | Resolve the vendor delete-path discrepancy and the native-mode unknowns. | Adapter correctness and Option A viability. | Follow verified vendor docs; stay on B. |

---

## 25. Terminal note

This document is design only. It adds no application code, no tests, no
credentials, no live calls, and no biometric media. It preserves the Stage 3
security and cleanup guarantees as hard invariants and keeps the Stage 4 gate
closed until the Verifier's contract is authored, reviewed and green on a
merged SHA.
