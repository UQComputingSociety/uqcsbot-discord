FROM python:3.13-slim AS python-base

# Environment variables that should exist in all images.
ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=2.4.1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_CACHE_DIR='/var/cache/pypoetry'


# poetry-base stage installs Poetry and installs prod deps
FROM python-base AS poetry-base

WORKDIR /app
RUN pip install "poetry==$POETRY_VERSION" && poetry --version

COPY pyproject.toml poetry.lock ./
RUN poetry install --without=dev


# dev stage continues off poetry-base to install dev deps
# and have poetry available within the container.
FROM poetry-base AS dev

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app
RUN poetry install --with=dev

ENTRYPOINT ["python", "-m", "uqcsbot"]


# prod stage creates the final image for production and excludes
# poetry as it is unneeded on prod.
FROM python-base AS prod

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=poetry-base /app /app

WORKDIR /app
COPY ./uqcsbot ./uqcsbot

# Run as a non-root user, nothing should be written to disk at runtime.
# We create this with a `/home/nonroot` home directory for the event
# that a depencendy decides to write to `~/.cache`.
RUN useradd --create-home --uid 65532 nonroot
USER nonroot

ENTRYPOINT ["python", "-m", "uqcsbot"]

