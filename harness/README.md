# Sah harness design

**This is a runnable integrity and smoke scaffold, NOT the complete acceptance harness.**

`python -m harness check --repo .` checks the file and mandate structure plus basic secret patterns. A PASS confirms only the planning files are correctly installed.

`python -m harness run --repo . --stage 1 --base-url http://127.0.0.1:8080` probes a running app's health and version shape. It deliberately exits 2 / marks the stage INCOMPLETE until an independent Harness Agent implements black-box checks for each spec. It must not be weakened to claim success.

## Harness agent implementation checklist
1. Publish deterministic fixtures and API schemas **before** feature code is written.
2. Implement cumulative `pytest` suites by stage (independent from production code); run in clean container against HTTP service only.
3. Add negative cases, concurrency/races, resets, unknown fields, repeat requests, vendor faults, privacy deletion and a separate live capability matrix.
4. Record all test names/versions/digests, counts and exit codes. No skipped/deselected tests counted green.
5. Isolate ports, mount artifacts, support `--mode isolated` with service+runner on private Docker network, no touching production keys.
6. Add claim-stage protection: a stage only counts when all stages <= N pass and stage-specific new capabilities are present.
7. Compare app behavior to human-readable specs. Do not write to the happy-path fixture only.

We intentionally do not ship fake passing suites; a green check on an empty app would undermine provenance and your learning objective.
