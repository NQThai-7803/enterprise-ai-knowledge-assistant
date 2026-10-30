# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_NO_COMPILE=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

WORKDIR /build

RUN python -m venv "${VIRTUAL_ENV}" \
    && python -m pip install --upgrade "pip>=25,<26" "setuptools>=80,<81" "wheel>=0.45,<0.46"

COPY requirements.lock ./

# The app uses CPU embeddings in the MVP; the lock pins the CPU Torch wheel. Installing it in its
# own layer keeps the large download cached when other pins change.
RUN python -m pip install --no-deps --index-url https://download.pytorch.org/whl/cpu \
        -c requirements.lock torch

# Install exactly the approved pins; --no-deps keeps pip from resolving anything outside the lock.
RUN python -m pip install --no-deps -r requirements.lock \
        --extra-index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install --force-reinstall --no-deps --index-url https://pypi.org/simple \
        -c requirements.lock typing_extensions \
    && python -m pip check \
    && python -c "from typing_extensions import Annotated; import alembic, fastapi, sqlalchemy"

# Bundle the default chunking encoding so runtime tokenization never downloads it.
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken
RUN python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"

FROM python:3.12-slim AS runtime

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    TIKTOKEN_CACHE_DIR=/opt/tiktoken \
    VIRTUAL_ENV=/opt/venv

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-vie \
    && rm -rf /var/lib/apt/lists/*
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app \
    && mkdir -p /app/data/uploads /app/data/models \
    && chown -R app:app /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /opt/tiktoken /opt/tiktoken
COPY --chown=app:app app ./app
COPY --chown=app:app alembic.ini pyproject.toml README.md ./

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS test

USER root
# Pinned test tools; packaging and pygments already come from requirements.lock.
RUN python -m pip install --no-cache-dir --no-deps \
        "pytest==9.2.0" "pluggy==1.7.0" "iniconfig==2.3.1" "ruff==0.17.3" \
    && python -m pip check
COPY --chown=app:app tests ./tests
USER app

CMD ["python", "-m", "pytest", "tests/unit", "-v"]