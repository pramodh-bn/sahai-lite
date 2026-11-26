# Base image pinned by digest for reproducibility (ADR 0001)
# python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b
FROM python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b

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
COPY requirements.lock ./requirements.lock

# Install dependencies
RUN pip install --no-cache-dir -r requirements.lock

# Copy application code
COPY main.py ./

# Change ownership to non-root user
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["python", "main.py"]