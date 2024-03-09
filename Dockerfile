FROM python:3.10-slim as python-base

# Environment variables that should exist in all images.
ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION=1.7.1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_CACHE_DIR='/var/cache/pypoetry'


# poetry-base stage installs Poetry and installs prod deps
FROM python-base as poetry-base

WORKDIR /app
RUN pip install "poetry==$POETRY_VERSION" && poetry --version

COPY pyproject.toml poetry.lock ./
RUN poetry install --without=dev


# dev stage continues off poetry-base to install dev deps
# and have poetry available within the container.
FROM poetry-base as dev

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app
RUN poetry install --with=dev

ENTRYPOINT ["python", "-m", "uqcsbot"]


# prod stage creates the final image for production and excludes
# poetry as it is unneeded on prod.
FROM python-base as prod

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=poetry-base /app /app

WORKDIR /app
COPY ./uqcsbot ./uqcsbot

ENTRYPOINT ["python", "-m", "uqcsbot"]

