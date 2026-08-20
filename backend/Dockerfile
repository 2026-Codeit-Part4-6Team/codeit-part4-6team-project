FROM ghcr.io/astral-sh/uv:0.11.32@sha256:df4cae8f3a96d175e2e5f992e597550000edbe78fdc2594d5cd8de1a217f504c AS uv

FROM python:3.11-slim@sha256:90744cff8f32887f075c47d747a173ff333e9e98801667af93c357fa9f5e28ff

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project \
    --only-group backend \
    --only-group model-consult \
    --only-group basic

COPY backend ./backend
COPY models ./models
COPY cache ./cache
COPY validation ./validation
COPY shared_data ./shared_data

EXPOSE 8000

CMD ["/bin/sh", "-c", "python -m backend.init_db && exec /app/.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
