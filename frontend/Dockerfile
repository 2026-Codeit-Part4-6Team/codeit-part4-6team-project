FROM ghcr.io/astral-sh/uv:0.11.32 AS uv

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --only-group frontend

COPY frontend/app.py ./frontend/app.py

EXPOSE 8501

CMD ["/app/.venv/bin/streamlit", "run", "frontend/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
