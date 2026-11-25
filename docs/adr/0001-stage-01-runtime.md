# ADR 0001: Stage 01 application runtime and container contract

- **Status:** Proposed
- **Date:** 2026-11-24
- **Issue:** ARCH-001
- **Stage:** 01 — Foundation and audit
- **Decision owner:** Architect
- **Required reviewer:** Reviewer seat
- **Base commit:** `f289c04b1958fb1765c574fd30c2dfb19d204eaf`

## Context

Stage 01 requires a cleanly buildable application with `GET /health` and
`GET /version`, deterministic offline behavior, safe degradation when vendor
credentials are absent, and truthful LIVE/MOCK labeling. The repository at the
base commit contains the independent Python harness but no application
manifest or accepted application framework.

Later stages need a deterministic rehearsal state machine, typed HTTP
contracts, idempotent mutations, vendor adapters, and potentially streaming
boundaries. Napster server-side SDK and handoff capabilities remain unverified;
the runtime choice must not invent or depend on them. Browser WebRTC concerns
also must not dictate the core API runtime.

A discarded Flask prototype proved only that Docker and the harness smoke
probe can reach the two endpoints. It was not delivered through the required
issue/worktree/review path and is not architecture or stage evidence.

## Decision drivers

1. Minimize the first real, reviewable Stage 01 slice.
2. Express request and response contracts as typed schemas.
3. Support asynchronous I/O without coupling core state transitions to a
   vendor SDK.
4. Align with the existing Python harness while keeping browser code separate.
5. Make container bytes, runtime mode, and tested source revision auditable.
6. Avoid host-port collisions and false-positive readiness probes.
7. Preserve a reversible path if verified vendor constraints later require a
   different adapter implementation.

## Options considered

| Option | Advantages | Costs and risks | Outcome |
| --- | --- | --- | --- |
| CPython 3.12 + FastAPI/Uvicorn | Typed OpenAPI/Pydantic contracts; ASGI async I/O; same language as the harness; small Stage 01 surface; natural adapter boundary | Python and a later browser client use different languages; dependency lock and worker policy must be explicit | **Selected** |
| CPython 3.12 + Flask | Very small smoke implementation; familiar synchronous request model | Development server is not a production runtime; typed contracts and async/streaming boundaries require additional patterns or later migration | Rejected as the root stack; acceptable only for labeled disposable fixtures |
| Node.js 24 + TypeScript | Shared types with a web client; strong browser/streaming ecosystem | Couples the first backend slice to an unverified browser/vendor surface; introduces a second test/toolchain before it adds Stage 01 value | Rejected for the core API; may still be used as a frontend build stage |

## Decision

Use **CPython 3.12.16**, **FastAPI**, and **Uvicorn** for the root application
API. FastAPI and Uvicorn versions and all transitive application dependencies
must be resolved by a committed lock file; mutable unconstrained installs are
not permitted.

This ADR selects an API runtime, not a monolith. The deterministic domain/FSM
layer must remain independent of FastAPI request objects and of Napster types.
A later frontend may use Node.js as a build tool without changing the shipped
Python runtime.

### Container image and platform policy

The shared Dockerfile must use this exact multi-architecture index reference:

```dockerfile
FROM python:3.12.16-slim-bookworm@sha256:44cf1793efa7c7a476bb0f2cff81443f4a072c90c1cb127e2924933daa3e8c64
```

The index digest preserves native architecture selection. CI must declare
`linux/amd64` explicitly and record the resolved child manifest in evidence:

- Multi-architecture index:
  `sha256:44cf1793efa7c7a476bb0f2cff81443f4a072c90c1cb127e2924933daa3e8c64`
- CI `linux/amd64` child:
  `sha256:1475c4f5b6bcb7d35e57661d6f5d7429ec4041275633c15f2b49350ac898276d`
- Native `linux/arm64/v8` child:
  `sha256:209c477b2d5268b578d813ae5a4668682b55252a5b32ad1148dd49e937119101`

The recorded verification command is:

```text
docker buildx imagetools inspect python:3.12.16-slim-bookworm@sha256:44cf1793efa7c7a476bb0f2cff81443f4a072c90c1cb127e2924933daa3e8c64 --format "{{json .Manifest}}"
```

It returned exit code 0 on 2026-11-24 and reported the index and child digests
above. A base-image refresh requires a dedicated reviewed supply-chain change;
changing only the tag is not an update.

The runtime image must:

- run as a non-root user;
- exclude `.git`, `runs/`, caches, local media, and secrets through a
  `.dockerignore`;
- install only locked runtime dependencies;
- receive version and Git SHA as immutable build metadata;
- use the application server, never a framework development server; and
- listen on `0.0.0.0:${PORT}` with `PORT=8080` as the documented default.

### HTTP service contract

#### `GET /health`

- Returns HTTP 200 with `Content-Type: application/json` and
  `{"status":"ok"}` only after routing and required local-store initialization
  are ready.
- Reports process readiness, not third-party availability.
- Missing Napster or model credentials must not make health report LIVE and
  must not be exposed in the response.

#### `GET /version`

Returns HTTP 200 JSON with these required fields:

```json
{
  "service": "sah",
  "version": "<immutable release or build version>",
  "git_sha": "<40 lowercase hexadecimal characters>",
  "mode": "MOCK"
}
```

`mode` is the effective runtime mode and is limited to `MOCK` or `LIVE`. It
defaults to `MOCK`. The application may report `LIVE` only when LIVE mode was
explicitly requested and its required configuration passed validation; process
startup alone is never evidence of live vendor behavior. Stage evidence must
separately prove any external capability.

The build must reject missing or placeholder version metadata rather than
serving `unknown` as an apparently immutable identity.

### Run and readiness contract

The container listens on port 8080, but local and CI runs publish it on an
ephemeral loopback host port, equivalent to:

```text
--publish 127.0.0.1::8080
```

The runner must:

1. assign a unique container name;
2. derive the host port from `docker port <name> 8080/tcp`;
3. verify the exact container ID, image reference, and running state before
   probing;
4. pass the derived URL to the harness; and
5. remove that exact container by name or ID during cleanup.

Fixed host ports are not the default because a foreign listener could satisfy
the probe and create a false pass. A fixed port may be used only after an
explicit preflight proves it is unbound and the run still verifies container
identity.

### State and concurrency boundaries

Stage 01 starts with one application process and one Uvicorn worker. This keeps
ordering observable while the durable event store and idempotency contracts are
not yet implemented. Increasing worker count is a later architecture change
and requires a shared durable store plus tests proving ordered transitions and
idempotent retries.

Domain transitions must execute behind an application service interface. HTTP
handlers validate and translate data; they do not own rehearsal state. This
prevents framework replacement or vendor adapter changes from rewriting the
FSM.

### Napster adapter boundary

The core application depends on a Sah-owned interface, not a Napster SDK type.
The interface may expose only capabilities independently verified by the API
Scout, such as session creation, input submission, event receipt, cancellation,
and cleanup. Each capability remains UNVERIFIED until supported by sanitized
documentation/probe evidence.

The adapter owns credentials, request correlation, single-flight/rate-limit
policy, bounded retries, spend accounting, cleanup, and truthful source labels.
Browser WebRTC remains at the client/media boundary unless verified evidence
requires a different design. No guessed endpoint or SDK feature enters the
domain contract.

## Migration and rollback

1. Do not merge or rebase the quarantined Flask prototype as implementation
   evidence. A backend issue must create the FastAPI application in its own
   worktree from the accepted base.
2. Preserve the externally tested Stage 01 endpoint semantics while replacing
   the prototype: `/health` stays exact; `/version` gains immutable SHA and
   explicit mode.
3. Stage 01 introduces no persistent product data migration. Any local schema
   introduced by implementation must be disposable and recreated in mock mode.
4. Rollback is a Git revert of the backend implementation PR and restoration
   of the last reviewed image digest. Do not retag a mutable image as rollback.
5. If a verified hard vendor constraint conflicts with this decision, open a
   superseding ADR. Prefer isolating a vendor-specific sidecar/adapter over
   replacing the deterministic core runtime.

## Consequences

### Positive

- The first application slice aligns with the existing harness and supports
  typed contracts.
- Async vendor calls can be isolated without making domain transitions async
  by accident.
- Image and source identity are explicit and reproducible for the CI platform.
- Ephemeral host ports and identity checks prevent the observed collision
  failure mode.

### Negative

- Backend and browser client code will not share a language or native types.
- A single worker limits throughput until durable concurrency semantics exist.
- Maintaining digest and dependency locks requires deliberate update PRs.

### Neutral / deferred

- This ADR does not verify Napster capabilities, complete Stage 01 acceptance
  tests, implement the application, update `stage-01/RUN.md`, or certify the
  stage.
- Deployment topology and persistent database choice remain future decisions.

## Verification and handoff

Acceptance for this ADR is:

```text
python -m harness check --repo .
```

The PR must also show the digest-inspection command and exit code, change only
this ADR path, carry the required agent attribution trailers, and receive an
independent review on the exact head SHA. After acceptance, the backend seat
implements the ASGI application in a separate issue/PR; the release integrator
then documents the real build/run commands and produces Stage 01 evidence.
