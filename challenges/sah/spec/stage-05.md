# Sah Stage 05: Avatar and media rendering

## Status
DRAFT — source of requirements for this proposed factory. Must be accepted in a PR before implementation. This stage is **cumulative**, extending all earlier stages. Prerequisite: Stage 04 PASS.

## User-visible goal
Double speaking while user watches.

## External contract
Clear stand-in identity, start/pause/stop, truthful LIVE/MOCK status, fallback, no concurrent overload.

## Required acceptance behavior
1. The implementation works from a clean checkout and `stage-05/RUN.md` without copying source files to another repo.
2. All earlier stage's tests remain green (highest contiguous stage, not isolated showcase).
3. Nominal flow succeeds on deterministic offline fixtures; no external API key is needed for mock tests.
4. Bad input, missing credentials, rate limits and interruption do not turn into fabricated success. Appropriate error/loading state is observable and tested.
5. Every feature has a stable ID or event and evidence pointing to the corresponding expected behavior.
6. Feature work is delivered via a per-agent branch/PR with issue, model, runtime, commits, test logs and independent review.

## Stage-specific evidence
Video player and media session lifecycle. Attach artifacts under `artifacts/stages/stage-05/` with real execution output. If vendor access is absent, mark BLOCKED and retain offline test results separately.

## Explicit non-goals
Do not introduce later-stage functionality to claim this stage early. Do not silently change requirements to match implementation. Do not claim real end-to-end avatar functionality based only on mock tests.

## Gate
`python -m harness run --repo . --stage 5 --base-url http://127.0.0.1:8080` and all earlier stages pass after the service is started. `python -m harness check --repo .` passes. Reviewer signs off on PR; CI passes; integration tag `stage-05-passed` may be created only after verified green results.

## Open design work
The Architect, Product Agent and Harness Engineer must turn the summarized external contract into detailed request/response JSON schemas and actual black-box test cases **before feature implementation**. This starter spec must not be treated as evidence that these tests already exist.
