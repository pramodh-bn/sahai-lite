# Handoff to sah-lead — Sah v3 Lite — Stage 3 cycle 2 (2026-11-25)

Purpose: overnight takeover of Stage 3 coordination. Resume from this file,
`factory-lite/STATUS.md`, and Git — not from memory.

## Current truth (verified)
- Integration branch: **`dev-v3`**. HEAD after the cycle-2 ledger merge:
  **`73ae4c08d1d50a7a49181fabce40f3e80382e268`** (PR #31 merged).
- Highest contiguous certified stage: **2**.
  - `lite-stage-1-passed` -> `93c817652192f037275f43406b741c1b089b8697`
  - `lite-stage-2-passed` -> `b0e276d52db7cdac643206b65c137b75f2ff251a`
- **Stage 3: UNCERTIFIED.** Cycle 1 blocked (Verifier integrity failures;
  the invented-routes contract **PR #22 is rejected and superseded — never merge**).
  Cycle 2 was opened by owner decision (Answer `E2AAB529`: *restart Verifier +
  new cycle*); the two-repair budget is **reset** for cycle 2.
- Worktrees: Lead integration = `D:\Workspace\sahai-lite-lead` (on `dev-v3`);
  Builder and Verifier use their own worktrees.

## Owner decision and inputs
- Owner supplied the **real, live-validated** Napster contract via the owner's
  own reference repo `D:\Workspace\koehashi` and the official docs at
  **`developers.napster.com`**.

## Root cause of the old block (corrected)
Stage-1 feasibility (`factory-lite/docs/napster-feasibility.md`) studied the
**legacy music-metadata API** at `developer.napster.com` (music metadata,
previews, playlists). The embodied agent the project needs is the
**Omniagent/Companion product at `developers.napster.com`** — a different host
and product. The old Verifier's "no vendor endpoint for the Sah handoff"
conclusion was true only for the wrong API surface.

## Real Napster contract (authoritative, non-invented)
1. **Create connection:** `POST https://napster-api.napster.com/public/agents/{agentId}/connections`
   — header `X-Api-Key`; body `{ channelType: "websocket" (realtime relay) or "webrtc" (live face), externalClientId, providerSettings.instructions }`.
   Bare `POST /public/connections` (no agent ref) returns **400 then 429** — not the contract.
2. **Cleanup:** `DELETE https://napster-api.napster.com/public/agents/{agentId}/connections/{connectionId}`.
3. **Face handoff:** the server POST returns **only** a short-lived, single-use
   token + connection id; the browser consumes it with the official Napster Web
   SDK `@touchcastllc/napster-companion-api` v2.0.0
   (`window.napsterCompanionApiSDK`; WebRTC signalling to
   `wss://avatar-signaling.napster.ai`). The API key never reaches the browser.
4. **Session/rate control:** bounded retry only for 409/429; single-flight queue
   + cooldown so the service never creates duplicate concurrent sessions.

References (same machine): `D:\Workspace\koehashi` — `stage-4/vendors.py`
(create / webrtc / cleanup / bounded retry / redaction), `stage-5/capacity.py`
(single-flight + cooldown), `stage-5/lib/PROVENANCE.md` (official SDK provenance
+ SHA-256 `c1b2db52...` + live Edge validation: `readyVideo`, `onAvatarReady`,
live `<video>`/`<audio>` mounted), `stage-4/RUN.md` (server->browser handoff).
Official docs: `developers.napster.com` — api-reference,
introduction/authentication, building-your-omniagent/managing,
`agents/{agentid}-connections-post`, `connections/{connectionid}-delete`.

## Actions already taken this session (Lead)
- Ledger updated and merged: **PR #31** -> `dev-v3` `73ae4c0`.
- Dispatched actionable assignment **LITE-S3-VERIFY-TESTS-02** to the Saha
  Verifier (base SHA `73ae4c0`) via a room reply (this agent's `band send` is
  refused).

## Open items / blockers for sah-lead
1. **Verifier runtime restart.** Owner chose "restart Verifier + new cycle".
   `band restart` is refused for *this* agent's permissions — needs the owner in
   Band Desktop, or sah-lead if its agent holds the grant. Confirm the Verifier
   is actually restarted before trusting its output.
2. **CLI permissions.** This agent's `band` CLI refuses
   `chat`/`peers`/`status`/`restart`/`send`. If sah-lead's agent holds these
   grants it can drive dispatch and restart directly.
3. **Verify the incoming contract.** When LITE-S3-VERIFY-TESTS-02 lands, check
   it: must fail against current `dev-v3` before implementation; must not invent
   routes; must not delete or weaken the Stage 1-2 baseline (49 cumulative
   tests); must carry a redacted live-probe evidence step that proves a live
   avatar/media state (`readyVideo`/mounted media), **not just a 200 token**.
   Reject a noncompliant contract without dispatching Builder.
4. **Two-repair limit** is reset for cycle 2; do not exceed it — stop and report
   on the second failure.

## Next actions (ordered)
1. Ensure the Verifier runtime is restarted.
2. Receive and verify the LITE-S3-VERIFY-TESTS-02 test contract; confirm it
   fails on current `dev-v3`; integrate the test-only PR after Lead review.
3. Then assign Builder implementation against that exact SHA.
4. Keep **Stage 4 gated**. Never push to `main`/`dev`/`dev-v3` directly; Lead
   merges via PR.

## Guardrails
- Do not log or print credentials. Owner-authorized live probe only.
- Do not merge PR #22. Preserve commits (no squash). No force pushes or
  destructive resets.
- Highest certified stage stays **2** until cumulative tests pass on a merged SHA.

Signed: Sahai Lead 2 (`@pramodh.nanjayya/sahai-lead-2`), 2026-11-25.
