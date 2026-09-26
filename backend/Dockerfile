FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.12.18
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
COPY backend/src ./src
COPY ai ./ai
RUN uv sync --frozen --no-dev \
    && useradd --uid 10001 --create-home shruti \
    && mkdir -p /data && chown -R shruti:shruti /app /data
USER shruti
ENV PATH="/app/.venv/bin:$PATH" SHRUTI_DATA_DIR=/data PYTHONPATH="/app:/app/src"
CMD ["uvicorn", "api.routes:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
