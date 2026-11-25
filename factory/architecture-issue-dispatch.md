# Architecture Issue Dispatch: Stage 1 Runtime Stack ADR

**Date:** November 24, 2026  
**Coordinator:** @pramodh.nanjayya/coordinator  
**Architect:** @pramodh.nanjayya/architect  
**Reviewer:** @pramodh.nanjayya/reviewer  
**Backend:** @pramodh.nanjayya/backend  
**Release Integrator:** @pramodh.nanjayya/release-integrator  

## Issue Details
- **Stage:** Stage-01 (Foundation and audit)
- **Spec IDs:** `s01-pref003-app-smoke` (Backend), `s01-pref003-integration-ci` (Release Integrator)
- **Base SHA:** `f289c04b1958fb1765c574fd30c2dfb19d204eaf`
- **Issue Type:** Architecture Decision Record (ADR)
- **Budget:** $0 external spend

## Dispatch Scope
**Select CPython 3.12.16 + FastAPI/Uvicorn runtime stack** with formal ADR covering:
1. **Technology Selection:** CPython 3.12.16 + FastAPI/Uvicorn over Flask and Node/TypeScript alternatives
2. **Digest/Platform Policy:** `python:3.12.16-slim-bookworm@sha256:44cf1793efa7c7a476bb0f2cff81443f4a072c90c1cb127e2924933daa3e8c64`, CI `linux/amd64`, record resolved child manifest
3. **Service Contracts:** Readiness (`/health`), version (`/version`), mode, ephemeral-port binding
4. **Boundaries:** Napster adapter interface, session management, companion creation
5. **Migration/Rollback:** Upgrade paths, backward compatibility, rollback procedures

## Dependencies
- ✅ **Preflight:** Harness validation (PR #4 approved), integration checkout (narrow claim lapsed)
- ✅ **Runtime Decision:** Release-integrator accepts architect as next owner
- ⚠️ **Blockers:** Commit 336fe94 governance issues resolved, backend worktree isolated

## Acceptance Criteria
1. **ADR Document:** Complete ADR following template with decision rationale, alternatives considered, consequences
2. **Evidence:** Digest verification (`docker buildx imagetools inspect`), platform compatibility check
3. **Review:** Independent reviewer assessment (@pramodh.nanjayya/reviewer)
4. **Integration:** ADR referenced in `stage-01/RUN.md` and backend implementation

## Acceptance Command
```
python -m harness check --repo .
git diff --exit-code
```

## Expected Evidence
1. ADR document in `docs/adr/` directory
2. Digest/platform verification logs
3. Service contract specification
4. Reviewer approval on ADR PR
5. Integration with backend implementation worktree

## Workflow
1. **Architect:** Create isolated issue worktree, write ADR, open PR
2. **Reviewer:** Independent review of ADR content and decisions
3. **Backend:** Implement selected stack in isolated worktree (`D:\Workspace\sahai-base-backend-s01-app`)
4. **Release Integrator:** Update `stage-01/RUN.md` with pinned commands, open PR
5. **Coordinator:** Verify integration and preflight completion

## Constraints
- **Budget:** $0 external spend (research/documentation only)
- **Time:** Preflight completion dependency
- **Governance:** Must follow agent protocol (trailers, independent review, small commits)
- **Integration:** Must work with existing harness and CI workflow

## Next Actions
1. **@pramodh.nanjayya/architect:** Create ADR worktree and PR
2. **@pramodh.nanjayya/reviewer:** Review ADR PR
3. **@pramodh.nanjayya/backend:** Await ADR approval, then implement
4. **@pramodh.nanjayya/release-integrator:** Update RUN.md after backend implementation
5. **@pramodh.nanjayya/coordinator:** Monitor progress, verify preflight completion

## References
- Stage-01 RUN.md (line 12: "after framework selection")
- Commit 336fe94 governance findings
- Architect recommendation: CPython 3.12.16 + FastAPI/Uvicorn
- Factory state tracking: `factory/state.json`

**Status:** DISPATCHED - GitHub Issue #6 created, awaiting architect ADR work