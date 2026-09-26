# Backend API and AI worker only. The studio frontend is deployed separately (Cloudflare Pages).
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.12.18
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
ARG INSTALL_INFERENCE=0
# Dependencies only: source edits must not invalidate this multi-GB layer.
# Code is importable through PYTHONPATH, so the project itself is not installed.
RUN if [ "$INSTALL_INFERENCE" = "1" ]; then \
        uv sync --frozen --no-dev --no-install-project --extra inference; \
    else \
        uv sync --frozen --no-dev --no-install-project; \
    fi \
    && useradd --uid 10001 --create-home shruti \
    && mkdir -p /data && chown shruti:shruti /data
COPY --chown=shruti:shruti backend/src ./src
COPY --chown=shruti:shruti ai ./ai
USER shruti
ENV PATH="/app/.venv/bin:$PATH" SHRUTI_DATA_DIR=/data PYTHONPATH="/app:/app/src" \
    HF_HOME=/data/models/hf SHRUTI_MODEL_CACHE_DIR=/data/models
CMD ["uvicorn", "api.routes:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
