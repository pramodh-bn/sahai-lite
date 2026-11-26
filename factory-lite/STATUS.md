# Status
Stage: 3
Cycle: 4 (owner-authorized fresh verification cycle; two-repair budget)
Task: LITE-S3-LIVE-CONTRACT-REPAIR-01-R2
Owner: Verifier 2
Coordinator: sah-lead
State: S3_CYCLE4_LIVE_CONTRACT_FINAL_REPAIR_ASSIGNED
Base SHA: bafa2021aeff5068201c24d1e7ae92eb01998f33
PR: https://github.com/pramodh-bn/sahai-lite/pull/45 (merged implementation)
Evidence: Verifier 2 repair 1 returned PR #50 head cd8a2e42e40fb9bf5f17fb9bacaebf00880a58c8 with correct scope, trailers, truthful four-test output, zero-call skip, fresh-target checks, actual-host derivation, exact POST status, telemetry, and a shared deadline helper. Lead static review found the exactly-once cleanup guard is still unsafe: it marks cleanup `sent` and increments the DELETE count before `disconnect_btn.click()` emits a request, so a click failure suppresses fallback cleanup and can orphan the resource. Both connect/disconnect clicks omit the remaining-deadline timeout; fallback `delete_napster_session` still has a fixed ten-second timeout outside the shared budget. Readiness and post-disconnect release are evaluated immediately rather than awaited, creating races against the real SDK callbacks and asynchronous cleanup. No live gate, credential read, or vendor call occurred. Highest certified stage remains 2; Stage 3 remains uncertified.
Next: Final Verifier repair 2 keeps PR #50 and must set cleanup-attempted/count only from an observed outgoing DELETE request, deadline-bound both clicks and fallback HTTP cleanup, await exact readiness/live media and post-disconnect resource release with remaining-time waits, and preserve the single-request/no-retry rule. The helper may accept an explicit timeout while retaining its default for existing offline tests. All prior guards, evidence semantics, four self-checks, zero-call gate, and 78-test suite must remain green. Any further failure blocks Cycle 4 live certification; no credentials or live calls are authorized during repair.
