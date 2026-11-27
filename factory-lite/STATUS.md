# Status
Stage: 4B
Cycle: 1 (owner-authorized 2026-11-27)
Task: LITE-S4B-VERIFY-TESTS-01
Owner: sah-stage4a-verifier (independent)
Coordinator: lead-3
State: S4B_AUTHORIZED
Base SHA: baa33b39bb043d37363e4ff5d0c2ea2acd0bb4f8
Prior closed PRs: #73 and #78 (never merge or reuse)
Evidence: On 2026-11-27 the owner authorized Stage 4B after Stage 4A core intelligence was certified at baa33b3. Stage 4A certified state: deliberate-red contract PR #81 (sah-stage4a-verifier), schema alias PR #82 (persona-architect), implementation PR #83 (sah-builder, 6 app files), independently verified by sah-stage4a-verifier — 161 tests exit 0, all Stage 1-3 green, immutable guard exit 0. Stage 4A is the last certified stage. Owner authorized continuation to 4B and 4C on 2026-11-27.
Next: sah-stage4a-verifier to author the LITE-S4B-VERIFY-TESTS-01 deliberate-red contract for Stage 4B consent/lifecycle. Scope: granular consent (rehearsal, avatar, mic, transcript save, research, subject consent), plus exactly-once session cleanup and retained-handle recovery observable through an application-connected fake HTTP vendor service wired through configuration (not test-owned). The app must create and delete against the fake vendor; the test observes the outcome at the application boundary. Contract must be tests/docs-only, run deliberate-red on base baa33b3, preserve all 161 existing tests (exit 0), and return one exact-head PR for Lead review before Builder 4B receives any assignment. 4C, Playwright, real vendor calls, credentials, and live calls remain inactive.
