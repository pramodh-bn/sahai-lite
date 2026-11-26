# Status
Stage: 3
Cycle: 4 (owner-authorized fresh verification cycle; two-repair budget)
Task: LITE-S3-LIVE-CONTRACT-REPAIR-01
Owner: Verifier 2
Coordinator: sah-lead
State: S3_CYCLE4_LIVE_CONTRACT_REPAIR_ASSIGNED
Base SHA: bafa2021aeff5068201c24d1e7ae92eb01998f33
PR: https://github.com/pramodh-bn/sahai-lite/pull/45 (merged implementation)
Evidence: Verifier 2 independently approved exact implementation head a08ffe0b22d302d403d48a3f267b65a1aaecca44 and reproduced 78 tests in 372.746 seconds, OK with one deliberate skip. Lead merged PR #45 unchanged at bafa2021aeff5068201c24d1e7ae92eb01998f33, then reproduced the focused gates/offline proof and the merged cumulative suite: 78 tests in 372.575 seconds, OK with one deliberate skip. Before enabling credentials, Lead inspected the frozen live module and found a blocking contract defect: it preallocates one Napster session through `post_napster_session`, then the browser click allocates a second independent session, while final cleanup explicitly deletes only the first. It also creates no required redacted evidence payload or artifact. Running it would violate the bounded one-resource/cleanup requirement and could not certify Stage 3. No live gate, credential read, or vendor call occurred. Highest certified stage remains 2; Stage 3 remains uncertified.
Next: Verifier 2 authors a narrowly scoped post-implementation test-contract repair from exact merged SHA bafa2021aeff5068201c24d1e7ae92eb01998f33. The repaired live module must create exactly one browser-owned vendor connection, capture its response only in memory, hash the real connection ID, prove exact SDK/media readiness, explicitly disconnect and verify server cleanup plus released browser media, generate and validate the required redacted evidence with real UTC timestamps, and guarantee best-effort cleanup on every failure path. Gate absent must remain a zero-call skip. No app change, credential use, or live run is authorized during contract repair. The test-only change requires separate Lead rationale/review under PROTOCOL.md before any live execution.
