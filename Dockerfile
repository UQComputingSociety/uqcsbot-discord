# ---- python-base
# Common Python runtime and environment settings shared by all stages.
FROM python:3.13-alpine AS python-base

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=2.4.1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_CACHE_DIR='/var/cache/pypoetry'


# ---- poetry-base
# Installs Poetry and production dependencies.
FROM python-base AS poetry-base

WORKDIR /app

RUN pip install "poetry==$POETRY_VERSION" && poetry --version

# Install production dependencies separately so source changes do not
# invalidate the dependency cache.
COPY pyproject.toml poetry.lock ./
RUN poetry install --without=dev --no-root


# ---- dev
# Development image with Poetry and development dependencies available for
# local development and testing.
FROM poetry-base AS dev

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN poetry install --with=dev --no-root

EXPOSE 8080
ENTRYPOINT ["python", "-m", "uqcsbot"]


# ---- prod
# Final production image. Excludes Poetry, build tooling, package manager,
# system shell, and runs as a non-root user. It only contains the application
# and virtual environment.
FROM python-base AS prod

# Create an unprivileged runtime user.
RUN addgroup -S -g 65532 nonroot                                \
 && adduser -S -G nonroot -u 65532 -h /home/nonroot nonroot

COPY --from=poetry-base --chown=nonroot:nonroot /app /app
COPY --chown=nonroot:nonroot ./uqcsbot /app/uqcsbot

WORKDIR /app

# Strip installer tooling from venv, and remove the package manager.
RUN /app/.venv/bin/pip uninstall -y pip setuptools wheel 2>/dev/null || true ; \
    rm -rf /sbin/apk /etc/apk /usr/share/apk /var/cache/apk

USER nonroot

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

EXPOSE 8080
ENTRYPOINT ["python", "-m", "uqcsbot"]
