# Sah Stage 07: Hidden needs and scoring

## Status
DRAFT — source of requirements for this proposed factory. Must be accepted in a PR before implementation. This stage is **cumulative**, extending all earlier stages. Prerequisite: Stage 06 PASS.

## User-visible goal
Deterministic persona + evidence-based judge.

## External contract
Hidden need defined before turn, rubric versions, apology/ask counts with excerpts, no leakage.

## Required acceptance behavior
1. The implementation works from a clean checkout and `stage-07/RUN.md` without copying source files to another repo.
2. All earlier stage's tests remain green (highest contiguous stage, not isolated showcase).
3. Nominal flow succeeds on deterministic offline fixtures; no external API key is needed for mock tests.
4. Bad input, missing credentials, rate limits and interruption do not turn into fabricated success. Appropriate error/loading state is observable and tested.
5. Every feature has a stable ID or event and evidence pointing to the corresponding expected behavior.
6. Feature work is delivered via a per-agent branch/PR with issue, model, runtime, commits, test logs and independent review.

## Stage-specific evidence
Positive and negative score fixtures. Attach artifacts under `artifacts/stages/stage-07/` with real execution output. If vendor access is absent, mark BLOCKED and retain offline test results separately.

## Explicit non-goals
Do not introduce later-stage functionality to claim this stage early. Do not silently change requirements to match implementation. Do not claim real end-to-end avatar functionality based only on mock tests.

## Gate
`python -m harness run --repo . --stage 7 --base-url http://127.0.0.1:8080` and all earlier stages pass after the service is started. `python -m harness check --repo .` passes. Reviewer signs off on PR; CI passes; integration tag `stage-07-passed` may be created only after verified green results.

## Open design work
The Architect, Product Agent and Harness Engineer must turn the summarized external contract into detailed request/response JSON schemas and actual black-box test cases **before feature implementation**. This starter spec must not be treated as evidence that these tests already exist.
