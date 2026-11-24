# Sah — BAND Desktop Autonomous Factory Starter Kit

**Status:** planning and harness scaffold, NOT a completed application and NOT a proven live Napster integration.

This kit is designed to be **merged** into an existing `D:\Workspace\sahai` Git repository and a working checkout created at `D:\Workspace\sahai-base`. Do not overwrite existing files blindly. It follows the *principles* of BAND's `sf-buildathon-2026`: role-specific mandates, progressive stage specifications, independent harness, reproducible runs, and durable provenance; it does **not** claim compatibility with BAND's organizer's original scoring harness.

## Getting started
1. Inspect your actual `sahai` repository, default branch, and uncommitted work; make a backup.
2. Copy this kit into the **repository** checkout, not into `.git` or a vendor API-key directory. Resolve collisions by merging.
3. Point BAND Desktop to `D:\Workspace\sahai-base` (after creating a Git worktree/clone). Repo is source of truth; base is the integration checkout. For simultaneous agents use isolated worktrees under `D:\Workspace\sahai-worktrees`, not the same checkout.
4. Create agents with the names in `agents/roster.json`, copy their `mandates/*.md` into BAND's instructions when supported. For Antigravity, prepend mandate text in each task (not a saved instructions field).
5. Give the Coordinator `MASTER_PROMPT.md` as the first task; check prerequisites, especially Git permissions, working models, Napster API and external avatar capabilities.
6. Run `python -m harness check --repo .` now. Later use `python -m harness run --repo . --stage 1 --base-url http://127.0.0.1:8080` with a running service. Run `python -m harness run --repo . --all --base-url ...` once cumulative stages are complete.
7. Every stage completion requires a real, green CI run and signed-off evidence in `artifacts/stages/stage-N/`, plus the PR history. A passing **scaffold inventory** is not a passing application.

## Files
- `MASTER_PROMPT.md`: main room dispatch prompt
- `FACTORY.md`: workflow, economic controls, gates and failure recovery
- `mandates/`: role definitions, generic (to preserve BAND's reuse philosophy)
- `agents/roster.json`: proposed runtime/model choices; calibrate to names in your BAND UI
- `challenges/sah/spec/stage-01.md` ... `stage-12.md`: cumulative product specifications
- `challenges/sah/manifest.json`: stages, requirements and evidence paths
- `harness/`: independent stage runner and evidence checker
- `stage-01/` ... `stage-12/`: per-stage delivery instructions (one shared application source tree rather than 12 code copies)
- `docs/`: architecture, Git protocol, human approvals, UI test plan
- `scripts/`: useful Git commands

## Honesty about autonomy
This zip cannot configure your machine, grant keys, run BAND Desktop for days, or guarantee vendor API behavior. A local always-on controller and permissions are prerequisites. No live tool, model or API has been tested by this kit.
