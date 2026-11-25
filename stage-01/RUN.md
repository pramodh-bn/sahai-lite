# Stage 01 — run and evidence

The **same root application** is used at each stage, with a Git tag recording the stage snapshot. This differs intentionally from the BAND event's complete copied stage directories, since all product, specs, and harness live in one repo.

## ADR 0001 Compliant Run Instructions

### 1. Prerequisites
- Docker with buildx support
- Git repository with full history
- Python 3.12+ for harness

### 2. Build Application
```bash
# Get current Git SHA for immutable build metadata
GIT_SHA=$(git rev-parse HEAD)

# Build with ADR 0001 compliant base image and build arguments
docker build \
  --platform linux/amd64 \
  --build-arg GIT_SHA="$GIT_SHA" \
  --build-arg APP_VERSION="1.0.0" \
  --build-arg SERVICE_NAME="sah" \
  --build-arg MODE="MOCK" \
  -t sah-stage1:$GIT_SHA \
  ./app
```

### 3. Run Container (Ephemeral Port)
```bash
# Run with ephemeral loopback port (ADR 0001 requirement)
CONTAINER_NAME="sah-harness-$GIT_SHA"
docker run -d \
  --name "$CONTAINER_NAME" \
  --publish 127.0.0.1::8080 \
  sah-stage1:$GIT_SHA

# Verify exact container identity before probing
CONTAINER_ID=$(docker ps -q -f name="$CONTAINER_NAME")
if [ "$(docker inspect "$CONTAINER_NAME" --format='{{.State.Status}}')" != "running" ]; then
  echo "ERROR: Container not running"
  exit 1
fi

# Get ephemeral host port
HOST_PORT=$(docker port "$CONTAINER_NAME" 8080/tcp | cut -d: -f2)
BASE_URL="http://127.0.0.1:$HOST_PORT"
echo "Service available at: $BASE_URL"

# Wait for service readiness
sleep 5
```

### 4. Verify Endpoints
```bash
# Health endpoint (process readiness only)
curl -f "$BASE_URL/health"

# Version endpoint (ADR 0001 required fields)
curl -f "$BASE_URL/version"
# Expected response:
# {
#   "service": "sah",
#   "version": "1.0.0",
#   "git_sha": "<40-character hex SHA>",
#   "mode": "MOCK"
# }
```

### 5. Run Harness Tests
```bash
# Scaffold integrity check
python -m harness check --repo .

# Stage 1 cumulative tests
python -m harness run --repo . --stage 1 --base-url "$BASE_URL"
```

### 6. Cleanup
```bash
# Remove exact container by name or ID (ADR 0001 requirement)
docker rm -f "$CONTAINER_NAME"
```

## Evidence Requirements

1. **Container Identity Verification**: Record exact `CONTAINER_ID`, image reference, and running state
2. **Endpoint Output**: Save sanitized JSON responses from `/health` and `/version`
3. **Harness Reports**: Save `runs/<timestamp>/report.json` from harness execution
4. **CI Evidence**: GitHub Actions workflow link with exit codes
5. **Reviewer Decision**: Formal GitHub review on PR head SHA

## Git Tag Protocol

Never tag `stage-01-passed` until:
- Every cumulative test has passed (smoke + acceptance)
- Real-vs-mock behavior is explicitly disclosed
- ADR 0001 compliance is verified
- Independent reviewer approval is recorded

## ADR 0001 Compliance Checklist
- ✅ Base image: `python:3.12.16-slim-bookworm@sha256:44cf1793...`
- ✅ Security: Non-root user runtime
- ✅ Dependencies: Locked transitive dependencies
- ✅ Build metadata: Git SHA and version injected
- ✅ Version endpoint: All required fields present
- ✅ `.dockerignore`: Excludes Git, runs/, media, secrets
- ✅ Container identity: Verified before probing
- ✅ Ephemeral ports: Used by default, fixed ports only with verification
- ✅ Cleanup: Exact container removal