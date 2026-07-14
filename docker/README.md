# Docker setup

Everything runs via `docker-compose.yml` at the repo root. This file
documents what's actually in it — there's no docker/ config beyond that
compose file and the `backend/Dockerfile` it builds.

## Services

| Service | Image | Container name | Purpose |
|---|---|---|---|
| `postgres` | `pgvector/pgvector:pg16` | `construction_ai_postgres` | Postgres 16 with the pgvector extension pre-installed. Holds the 18 dataset tables + 4 AI-layer tables. |
| `redis` | `redis:7-alpine` | `construction_ai_redis` | Provisioned for future use (caching, task queues). Nothing in the current build reads or writes it yet. |
| `api` | built from `backend/Dockerfile` | `construction_ai_api` | FastAPI app (`uvicorn --reload`), the agent framework, APScheduler. |

`postgres` and `redis` have healthchecks; `api` won't start until both
report healthy (`depends_on: condition: service_healthy`).

## Ports (published to the host)

| Port | Service | Notes |
|---|---|---|
| `8000` | api | FastAPI / Swagger UI at `/docs` |
| `5432` | postgres | For connecting a local DB client (psql, DBeaver, etc.) |
| `6379` | redis | Unused by the app currently; published for inspection only |

## Volumes

**Named (Docker-managed) volumes** — persist across `docker compose down`,
wiped by `docker compose down -v`:

- `postgres_data` → `/var/lib/postgresql/data`
- `redis_data` → `/data`

**Bind mounts** (api service only) — live-sync specific `backend/`
subdirectories into the running container so edits take effect without a
rebuild (`uvicorn --reload` picks up `app/` changes; scripts/tests just
need to exist on next `docker exec`):

- `./backend/app` → `/app/app`
- `./backend/alembic` → `/app/alembic`
- `./backend/scripts` → `/app/scripts`
- `./backend/tests` → `/app/tests`

Everything else needed inside the container (`requirements.txt`,
`alembic.ini`, `pytest.ini`) is baked in via `COPY` in the Dockerfile at
build time — those rarely change, so a rebuild (`docker compose up -d
--build api`) is the right way to pick up edits to them, rather than
another bind mount.

**Not mounted at all:** anything above `backend/` (repo root files like
`README.md`, `docs/`, `DEMO_GUIDE.md`) is invisible inside the container.
Scripts that need to write output back to the repo root (e.g.
`seed_demo_data.py`) write under the mounted `scripts/` dir instead, and
the caller moves the file to the repo root on the host side.

## Common commands

```bash
docker compose up -d --build     # start everything, rebuild api if changed
docker compose down              # stop, keep data volumes
docker compose down -v           # stop and wipe all data (fresh start)
docker compose logs -f api       # tail api logs
docker compose restart api       # restart api only (does NOT re-read .env
                                  #   or pick up a Dockerfile change -- use
                                  #   `up -d --build` for that)
```

See the [Makefile](../Makefile) at the repo root for shortcuts
(`make dev`, `make down`, `make logs`, `make test`).
