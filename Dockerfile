# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.10

## --------------------------- Builder Stage ---------------------------
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH"

RUN apt-get update && apt-get install --no-install-recommends -y \
        build-essential curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ADD https://astral.sh/uv/install.sh /install.sh
RUN chmod -R 655 /install.sh && /install.sh && rm /install.sh

WORKDIR /app

COPY requirements.txt .
RUN uv venv && uv pip install -r requirements.txt

## --------------------------- Prod Stage ---------------------------
FROM python:${PYTHON_VERSION}-slim AS prod

RUN useradd --create-home appuser
USER appuser

WORKDIR /app

COPY ./app ./app
COPY ./alembic ./alembic
COPY ./alembic.ini ./alembic.ini
COPY --from=builder /app/.venv .venv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
