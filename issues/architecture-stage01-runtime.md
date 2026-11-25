# Architecture Issue: Stage-01 Runtime Stack ADR

**Issue ID:** ARCH-001  
**Created:** November 24, 2026  
**Coordinator:** @pramodh.nanjayya/coordinator  
**Architect:** @pramodh.nanjayya/architect  
**Reviewer:** @pramodh.nanjayya/reviewer  
**Status:** DISPATCHED

## Issue Details
- **Base SHA:** `f289c04b1958fb1765c574fd30c2dfb19d204eaf`
- **Stage:** Stage-01 (Foundation and audit)
- **Spec IDs:** `s01-pref003-app-smoke` (Backend), `s01-pref003-integration-ci` (Release Integrator)
- **Budget:** $0 external spend
- **Worktree:** Isolated issue worktree (not `sahai-base`)

## Authorized Path
**ADR File Path:** `docs/adr/0001-stage-01-runtime.md`  
*Note: This is the only product/spec path this issue permits.*

## Acceptance Command
```
python -m harness check --repo .
```
**Plus documented run/evidence step:** ADR review is a docs change, so no stage certification rides on it.

## Independent Reviewer
**Reviewer:** @pramodh.nanjayya/reviewer  
*Note: Reviewer seat other than architect and backend.*

## Scope
**Select CPython 3.12.16 + FastAPI/Uvicorn runtime stack** with formal ADR covering:

1. **Technology Selection:** CPython 3.12.16 + FastAPI/Uvicorn over Flask and Node/TypeScript alternatives
2. **Digest/Platform Policy:** 
   - Multi-arch index digest in shared Dockerfile (for arm64 compatibility)
   - `linux/amd64` declared for CI
   - Resolved child manifest `sha256:44cf1793efa7c7a476bb0f2cff81443f4a072c90c1cb127e2924933daa3e8c64` recorded in run evidence
3. **Service Contracts:** Readiness (`/health`), version (`/version`), mode, ephemeral-port binding
4. **Boundaries:** Napster adapter interface, session management, companion creation
5. **Migration/Rollback:** Upgrade paths, backward compatibility, rollback procedures

## Dependencies
- ✅ **Preflight:** Harness validation (PR #4 approved), integration checkout (narrow claim lapsed)
- ✅ **Runtime Decision:** Release-integrator accepts architect as next owner
- ⚠️ **Quarantine:** Commit 336fe94 and backend branch `ba23702` not reviewable evidence

## Evidence Requirements
1. ADR document following template
2. Digest/platform verification logs
3. Service contract specification
4. Reviewer approval on ADR PR
5. Integration with backend implementation worktree

## Fixed Sequence
1. **Architect:** Create ADR in isolated worktree, open PR for `docs/adr/0001-stage-01-runtime.md`
2. **Reviewer:** Independent ADR review
3. **Backend:** ASGI implementation PR on digest `44cf1793…8c64`
4. **Release Integrator:** RUN.md + stage-evidence PR
5. **Coordinator:** Verify integration and preflight completion

## Constraints
- **Worktree:** Must be isolated issue worktree, not `sahai-base`
- **Evidence:** Must record both index digest (source reference) and child manifest (CI actual pull)
- **Governance:** Must follow agent protocol (trailers, independent review, small commits)
- **Integration:** Must work with existing harness and CI workflow

## Current Status
- **PREFLIGHT-REL-003:** Not accepted
- **Stage 1 Application Smoke:** Open (awaiting ADR → backend implementation)
- **Branch Protection:** Open (HTTP 403)
- **Integration Checkout:** `sahai-base` clean at `f289c04b`

## Next Action
**@pramodh.nanjayya/architect:** Proceed with ADR creation in isolated worktree.

---
*Coordinator-issued architecture issue. Reference: `factory/architecture-issue-dispatch.md`*