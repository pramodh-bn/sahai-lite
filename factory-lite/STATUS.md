# Status
Stage: 3
Task: LITE-S3-CAPABILITY-PROBE-01
Owner: Verifier
Coordinator: sah-lead
State: S3_LIVE_CAPABILITY_DISCOVERY_AUTHORIZED
Base SHA: 29b39bfb2feee94311614a5b97af13f25f39c389
PR: none; rejected Stage 3 contract PR #22 remains unmergeable at e1dad9059ad624f7af238ad6004fbde170482618
Evidence: Owner explicitly authorized a tightly bounded Napster capability-discovery probe in room message 4282d614-65eb-4846-818f-ed9f2b5d9059. Protected credentials are available only from D:\Workspace\sahai-lite\.secrets\sahai-lite.env as NAPSTER_API_KEY and NAPSTER_AGENT_ID; .secrets and sahai-lite.env are ignored locally and on dev-v3, and no credential value may be printed, logged, committed, or copied into evidence. This authorization reopens Stage 3 after the prior two-repair blocker only for discovery; Stage 3 remains uncertified and Stage 2 remains certified/tagged at b0e276d52db7cdac643206b65c137b75f2ff251a.
Next: Verifier must run one owner-authorized, bounded live capability-discovery assignment against official Napster surfaces, with a strict call budget, no subscription/account/resource upgrades, immediate stop on billing/quota/credit or unsupported-capability responses, mandatory cleanup, and redacted evidence. Use the result to define a new official test-first contract or report the exact remaining blocker. Builder and Stage 4 remain gated.
