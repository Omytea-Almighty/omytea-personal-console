# Omytea Personal Future Console — container distribution.
#
# Multi-stage:
#   1. builder — install python + deps + warm pip cache
#   2. runtime — minimal: copy deps + source, expose port 8501
#
# Build:
#     docker build -t omytea-console:0.3 .
#
# Run (mock mode, no Ollama needed):
#     docker run --rm -p 8501:8501 -e OMYTEA_CONSOLE_MOCK=1 omytea-console:0.3
#     # then open http://localhost:8501
#
# Run (vision mode, expects an Ollama host reachable from the container):
#     docker run --rm -p 8501:8501 \
#         -e OLLAMA_HOST=http://host.docker.internal:11434 \
#         omytea-console:0.3
#
# Run (with persistent SQLite via a mounted volume):
#     docker run --rm -p 8501:8501 \
#         -v "$HOME/.omytea-personal-console:/data" \
#         -e HOME=/data \
#         omytea-console:0.3
#
# Master plan §15 Rule #11 — image is provider-neutral, runs offline
# in mock mode without any external API call.

FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

# OpenCV headless needs a tiny set of native libs at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_MAX_UPLOAD_SIZE=200

# Same native deps the builder needs at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Pull in the prebuilt site-packages tree from the builder stage
COPY --from=builder /install /usr/local

WORKDIR /app
COPY . /app

# Add a non-root user so the container doesn't run as root by default
RUN useradd --create-home --shell /bin/bash omytea
USER omytea

EXPOSE 8501

# Liveness / readiness — same endpoint streamlit exposes natively
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py"]
