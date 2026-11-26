# Status
Stage: 3
Cycle: 5 (owner-authorized fresh live-contract verification cycle; two-repair budget)
Task: LITE-S3-LIVE-CONTRACT-02
Owner: Verifier 2
Coordinator: sah-lead
State: S3_CYCLE5_LIVE_CONTRACT_ASSIGNED
Base SHA: 1940cad05d6a135d24424d2e955af3cdc8a72d02
PR: https://github.com/pramodh-bn/sahai-lite/pull/45 (merged implementation)
Evidence: Owner explicitly authorized a fresh verification cycle after Cycle 4 blocked. The merged app already exposes `NAPSTER_BASE_URL` with official default `https://companion-api.napster.com`; no new Builder URL configuration is required. Cycle 5 is limited to a fresh Verifier-authored live contract that keeps loopback available for offline fake-vendor tests but categorically rejects loopback, localhost, private/test hosts, unsupported schemes, and any non-approved host when `SAH_NAPSTER_LIVE=1`. Rejected PR #50 stays closed and its commit history must not merge or be reused. No live gate, credential read, paid call, or vendor call has occurred. Offline Stage 3 implementation remains independently green at 78 tests with one deliberate skip. Highest certified stage remains 2; Stage 3 remains uncertified.
Next: Verifier 2 authors a new tests/docs-only contract from exact current base 1940cad05d6a135d24424d2e955af3cdc8a72d02 on a new branch/worktree. The contract must retain the validated single browser-owned flow, shared 30-second deadline, request-observed exactly-once cleanup, real readiness/media/release evidence, fresh atomic redacted artifact, and truthful self-checks, while separating offline host validation from live certification. Live mode must accept only an explicit approved Napster host and evidence certification must independently reject loopback. No credentials or live execution are authorized during contract authoring.
