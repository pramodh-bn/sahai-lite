# Status
Stage: 3
Cycle: 3 (owner-authorized replacement Verifier; fresh two-repair budget)
Task: LITE-S3-VERIFY-TESTS-03-R1
Owner: Verifier 2
Coordinator: sah-lead
State: S3_CYCLE3_TEST_CONTRACT_REPAIR_1_ASSIGNED
Base SHA: f9c1f41517786e58e9c459ecb7d454362a43a2b1
PR: https://github.com/pramodh-bn/sahai-lite/pull/38
Evidence: Verifier 2 delivered origin head 809abb5010691bc90192b8d6d9e1b8b96610576a on a correctly based, test/docs-only PR with valid trailers and a preserved 49-test baseline. Lead rejected the first contract result after static review found blocking validity gaps: the live test did not assert readyVideo/onAvatarReady or live audio; retry cases reused an active session; cleanup-on-error was not exercised; single-flight was sequential rather than concurrent; cooldown had no test; and the documentation named unsupported api.napster.com instead of separating the current official companion-api.napster.com host from the historical napster-api.napster.com alias. Repair 1 keeps the same branch and PR. Highest certified stage remains 2; Stage 3 remains uncertified.
Next: Verifier 2 must repair PR #38, preserve all 49 prior tests, and return an unchanged-scope head with genuine browser/media certification, isolated retries, observable success/error cleanup, concurrent single-flight plus cooldown, corrected host provenance, and a stable zero-call gate-absent command. Lead will independently reproduce the repaired contract before integration. Builder and Stage 4 remain gated.
