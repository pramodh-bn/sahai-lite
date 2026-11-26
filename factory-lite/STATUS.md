# Status
Stage: 3
Cycle: 4 (owner-authorized fresh verification cycle; two-repair budget)
Task: LITE-S3-LIVE-CONTRACT-REPAIR-01-R1
Owner: Verifier 2
Coordinator: sah-lead
State: S3_CYCLE4_LIVE_CONTRACT_REPAIR_1_ASSIGNED
Base SHA: bafa2021aeff5068201c24d1e7ae92eb01998f33
PR: https://github.com/pramodh-bn/sahai-lite/pull/45 (merged implementation)
Evidence: Verifier 2 returned test/docs-only PR #50 at head 3b1eb4dd9688ea006d56567c7596973367329d76. Scope, ancestry, trailers, preserved original four self-checks, zero-call/zero-artifact gate skip, single browser-owned flow, hashing, evidence validation, and atomic output structure are valid. Lead static review rejected credentialed execution because the 30-second bound is only asserted after independent waits of 10, 25, 25, 25, and 5 seconds, so the test can violate the owner-authorized duration before failing. Cleanup also clicks disconnect, waits a fixed one second, then may issue a fallback DELETE if the asynchronous response has not arrived; this can perform two cleanup operations and violate the one-cleanup bound. The evidence hardcodes the default host and substitutes status 200 when no status was observed. Verifier's terminal report also listed self-check names that do not match the committed four tests. No live gate, credential read, or vendor call occurred. Highest certified stage remains 2; Stage 3 remains uncertified.
Next: Verifier 2 repair 1 keeps PR #50 and must enforce one shared deadline across every wait and cleanup, observe the disconnect response deterministically rather than sleeping, guarantee at most one cleanup request including failure paths, fail prominently without retry if that cleanup fails, require the observed POST status to be exactly 200, record the actual configured vendor host, use a fresh non-existing evidence target, and return exact truthful command/test names. It must preserve all prior contract assertions and re-run the 4-test self-check, zero-call/zero-artifact gate, and 78-test cumulative suite. No credentials or live calls are authorized during repair.
