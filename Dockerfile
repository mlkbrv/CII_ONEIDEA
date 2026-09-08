# Two frontends and one backend in a single image.
#
# The API serves the built Mini App and admin panel itself, so there is one
# artefact to deploy, one origin, and no separate web server to configure —
# which also sidesteps mixed-content rules that Telegram Mini Apps enforce.

# --- Stage 1: build the frontends ------------------------------------------
FROM node:22-slim AS frontend
WORKDIR /build

# Manifests first: this layer only rebuilds when dependencies change, so the
# slow npm install is cached across ordinary code edits.
COPY miniapp/package*.json miniapp/
COPY admin/package*.json admin/
RUN cd miniapp && npm ci --no-audit --no-fund \
 && cd ../admin && npm ci --no-audit --no-fund

COPY miniapp miniapp
COPY admin admin
RUN cd miniapp && npm run build \
 && cd ../admin && npm run build


# --- Stage 2: the runtime ---------------------------------------------------
FROM python:3.12-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY pyproject.toml alembic.ini ./
COPY app ./app
# Installed after the source is in place because pyproject declares the `app`
# package; a wheel built without it would install nothing.
RUN pip install --no-cache-dir .

COPY alembic ./alembic
COPY media ./media
COPY scripts ./scripts

# Only the built output, not node_modules or sources.
COPY --from=frontend /build/miniapp/dist ./miniapp/dist
COPY --from=frontend /build/admin/dist ./admin/dist

EXPOSE 8000

# Migrations run here rather than in an entrypoint script so a failed upgrade
# stops the container loudly instead of starting an API against a schema it
# does not match. The worker waits for the API's healthcheck, so exactly one
# process ever runs them.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
