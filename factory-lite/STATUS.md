# Status
Stage: 3
Cycle: 5 (owner-authorized fresh live-contract verification cycle; two-repair budget)
Task: LITE-S3-LIVE-CONTRACT-02-R2
Owner: Verifier 2
Coordinator: sah-lead
State: S3_CYCLE5_LIVE_CONTRACT_REPAIR_2_ASSIGNED
Base SHA: 1940cad05d6a135d24424d2e955af3cdc8a72d02
PR: https://github.com/pramodh-bn/sahai-lite/pull/45 (merged implementation)
Evidence: Repair 1 was independently accepted and PR #55 merged unchanged at `0ca539b42cfb39fcb2b9e6af11b8958177c2471b`; Lead reproduced 85 tests in 373.055s, `OK (skipped=1)`, plus 19/19 focused safeguards. Under the owner's instruction to try again, Lead ran the single bounded credentialed probe against exact HTTPS `companion-api.napster.com`. The SDK bundle loaded and mounted its `<video>`, but the element stayed hidden and no live media/readiness arrived before the 30-second bound. No app `/napster-session` POST was observed, so no vendor connection was created. The one fallback DELETE returned HTTP 200 with `status=no_active_connection`, confirming no active vendor resource remained; the contract incorrectly treated that safe idempotent state as possible retention and masked the original readiness timeout. No evidence artifact was written and no credential value was exposed. Stage 3 remains uncertified.
Next: Final Verifier repair 2 must make the live browser deterministic for headless microphone permission without real-person capture by launching Chromium with fake media permission/device inputs or an equally bounded non-personal mechanism, while preserving the real remote avatar/video/audio readiness requirements. It must treat a single HTTP 200 `no_active_connection` fallback response as cleanup-safe only when zero app connection POSTs were observed; certification must still fail on the original readiness error and must never claim live success without one observed POST, exact readiness/media, and one cleanup. Add offline executable/static regressions for both behaviors, preserve all prior assertions and the official-host boundary, and perform no credential or live call during repair. This is repair 2 of 2; any further failure blocks Cycle 5.
