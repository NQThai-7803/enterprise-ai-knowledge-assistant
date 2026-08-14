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

# The app uses CPU embeddings in the MVP; preinstalling CPU Torch avoids CUDA wheels in the image.
RUN python -m pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.3,<3"

COPY pyproject.toml ./

RUN python -c "import subprocess, sys, tomllib; deps = tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']; subprocess.check_call([sys.executable, '-m', 'pip', 'install', *deps])" \
    && python -m pip install --force-reinstall --no-deps --index-url https://pypi.org/simple "typing_extensions>=4.12,<5" \
    && python -m pip check \
    && python -c "from typing_extensions import Annotated; import alembic, fastapi, sqlalchemy"

FROM python:3.12-slim AS runtime

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
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
COPY --chown=app:app app ./app
COPY --chown=app:app alembic.ini pyproject.toml README.md ./

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS test

USER root
RUN python -m pip install --no-cache-dir "pytest>=8.0.0" "ruff>=0.6.0"
COPY --chown=app:app tests ./tests
USER app

CMD ["python", "-m", "pytest", "tests/unit", "-v"]