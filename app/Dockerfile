# Base image pinned by digest for reproducibility (ADR 0001)
# python:3.12.16-slim-bookworm@sha256:44cf1793efa7c7a476bb0f2cff81443f4a072c90c1cb127e2924933daa3e8c64
FROM python:3.12.16-slim-bookworm@sha256:44cf1793efa7c7a476bb0f2cff81443f4a072c90c1cb127e2924933daa3e8c64

# Build metadata (Git SHA and version)
ARG GIT_SHA
ARG APP_VERSION=1.0.0
ARG SERVICE_NAME=sah
ARG MODE=MOCK

# Runtime environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    APP_VERSION=${APP_VERSION} \
    SERVICE_NAME=${SERVICE_NAME} \
    MODE=${MODE} \
    GIT_SHA=${GIT_SHA}

# Create non-root user (ADR 0001 security requirement)
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy dependency files first for better caching
COPY requirements.txt ./requirements.txt
COPY requirements.lock ./requirements.lock

# Install locked dependencies (ADR 0001 lock file requirement)
RUN pip install --no-cache-dir -r requirements.lock

# Copy application code
COPY main.py ./

# Change ownership to non-root user
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["python", "main.py"]