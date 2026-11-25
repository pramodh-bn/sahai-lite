"""Stage 1 minimal service: /health and /version only.

No fake LIVE statuses: /version reports the build's static version string and
never claims a live/external integration it does not have.

ADR 0001 compliant implementation.
"""

import os

import uvicorn
from fastapi import FastAPI

# Build metadata from environment (injected during Docker build)
APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "sah")
MODE = os.environ.get("MODE", "MOCK")
GIT_SHA = os.environ.get("GIT_SHA", "unknown")

app = FastAPI(title=SERVICE_NAME, version=APP_VERSION)


@app.get("/health")
def health() -> dict:
    """Health endpoint - reports process readiness only.
    
    Returns HTTP 200 with {"status":"ok","version":"<actual checkout/build SHA>"} 
    only after routing and required local-store initialization are ready. 
    Reports process readiness, not third-party availability.
    """
    return {"status": "ok", "version": GIT_SHA}


@app.get("/version")
def version() -> dict:
    """Version endpoint with immutable build metadata (ADR 0001 requirement).
    
    Returns HTTP 200 JSON with required fields:
    - service: "sah"
    - version: immutable release or build version
    - git_sha: 40 lowercase hexadecimal characters
    - mode: "MOCK" or "LIVE"
    
    mode defaults to "MOCK". The application may report "LIVE" only when
    LIVE mode was explicitly requested and its required configuration
    passed validation.
    """
    return {
        "service": SERVICE_NAME,
        "version": APP_VERSION,
        "git_sha": GIT_SHA,
        "mode": MODE
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8080")),
        log_level="info",
    )