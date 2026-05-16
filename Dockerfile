FROM python:3.10

ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV WEB_CONCURRENCY=4

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH"

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-workspace --package app

COPY pyproject.toml uv.lock alembic.ini ./
COPY app ./app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --package app

CMD ["bash", "-c", "python app/backend_pre_start.py && alembic upgrade head && python app/initial_data.py && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY}"]
