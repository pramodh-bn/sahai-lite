# Status
Stage: 3
Task: LITE-S3-CAPABILITY-PROBE-01
Owner: Verifier
Coordinator: sah-lead
State: S3_LIVE_CAPABILITY_DISCOVERY_REPAIR_REQUESTED_1
Base SHA: 29b39bfb2feee94311614a5b97af13f25f39c389
PR: none; rejected Stage 3 contract PR #22 remains unmergeable at e1dad9059ad624f7af238ad6004fbde170482618
Evidence: Owner expanded authorization in room message 79790580-55f5-4cb6-931e-437c67f4fa96 to cover the probe and test and confirmed sufficient credit. Verifier returned BLOCKED without attempting network access. Lead independently found the current official contract: `https://companion-api.napster.com`; `GET /public/agents/{agentId}` for read-only preflight; `POST /public/agents/{agentId}/connections` with WebRTC/video for one transient session; and `DELETE /public/connections/{connectionId}` for cleanup. Official Web SDK documentation defines avatar rendering through `onAvatarReady` and media cleanup through `destroy()`. No credential or live call was made by Lead. Stage 3 remains uncertified and Stage 2 remains certified/tagged at b0e276d52db7cdac643206b65c137b75f2ff251a.
Next: Verifier repair 1 must attempt exactly the documented bounded three-operation sequence (or only the read-only GET if preflight fails), capture redacted evidence, and author a new official test-first contract requiring the later Builder implementation to prove Web SDK avatar/audio readiness plus cleanup and app-local handoff. No invented endpoints, retries, upgrades, fallback providers, raw IDs, tokens, or credentials. Builder and Stage 4 remain gated.
