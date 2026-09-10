# Deployment Direction

T06e provides a preview-ready single-container deployment.

```bash
docker compose up -d
```

The default image is `ghcr.io/ledomme/stashive:edge`; set `STASHIVE_IMAGE` to
`ghcr.io/ledomme/stashive:pr-N` when testing a pull request. The container
serves the UI and `/api` on port 8000, runs Alembic migrations on startup, and
persists SQLite under `/app/data` via the `stashive-data` volume. First-run setup
tokens are written to container logs. Set `AUTH_COOKIE_SECURE=true` behind HTTPS.
Retrieve a first-run token with `docker logs stashive` or `docker compose logs stashive`.

## Default production goal

Simple:

```text
stashive container
  |
  +-- application
  +-- built frontend
  +-- SQLite
       |
       +-- persistent /app/data
```

The database must never live only in the ephemeral container layer.

## Environment direction

Likely variables:

```text
STASHIVE_DATA_DIR=/app/data
DATABASE_URL=sqlite:////app/data/stashive.db
```

Additional variables must be introduced only when needed.

## PostgreSQL

Optional later:

```text
DATABASE_URL=postgresql+psycopg://...
```

The app must not require PostgreSQL for normal self-hosting.

## Reverse proxy

Expected deployments may place Stashive behind:
- Traefik
- nginx
- Caddy
- similar reverse proxies

Do not hard-code public hostnames.

## Backup

For SQLite, backup documentation must eventually cover:
- application-safe DB backup
- artwork/data files
- restore verification

A built-in backup CLI may be considered later, but is not a v0.1 requirement.

## Production image

Production image should eventually:
- run non-root
- include only runtime dependencies
- include built frontend
- expose health endpoint
- use persistent data mount
- support graceful shutdown

Do not over-engineer container permissions during early application milestones.
