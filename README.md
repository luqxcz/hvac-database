# HVAC Time-Series Database (TimescaleDB + SQLAlchemy)

A minimal, production-friendly time-series database for HVAC telemetry built on PostgreSQL + TimescaleDB. It uses SQLAlchemy ORM models to define schema (sites, devices, points, measurements), initializes a Timescale hypertable, and configures compression and retention policies.

- ORM models live in `db/models.py`
- Initialization script is `init_db.py`
- Containerized via `docker-compose.yml`
- Migrations scaffolded via Alembic in `migrations/`
- ERD artifacts live in `docs/`

## Features
- TimescaleDB hypertable on `measurements` using time (`measurement_timestamp`) and space (`point_id`) dimensions
- Automatic compression policy and retention policy
- UUID primary keys for core entities, JSONB tags on points
- Alembic migrations directory included

## Quickstart (Docker)
Prereqs: Docker and Docker Compose.

```bash
# From project root
docker compose up --build
```
This will:
- Start TimescaleDB (PostgreSQL 15 base)
- Run `init_db.py` in the app container
- Ensure the `timescaledb` extension is available
- Create/update tables defined in `db/models.py`
- Make `measurements` a hypertable and set compression/retention policies

Connect to the database locally (defaults shown):
```bash
psql -h localhost -p 5432 -U postgres -d hvac
# password: postgres (default)
```

## Configuration
The app reads environment variables (see `docker-compose.yml` and `init_db.py`):

- `POSTGRES_HOST` (default: `db` in Docker, use `localhost` locally)
- `POSTGRES_PORT` (default: `5432`)
- `POSTGRES_DB` (default: `hvac`)
- `POSTGRES_USER` (default: `postgres`)
- `POSTGRES_PASSWORD` (default: `postgres`)
- `ALLOW_DESTRUCTIVE_INIT` (default: `0`) — if `1`, init may drop unmanaged legacy tables
- `COMPRESS_AFTER_DAYS` (default: `7`) — when to compress old chunks
- `RETAIN_DAYS` (default: `365`) — retention policy for old data

You can override these via Compose environment or a `.env` file.

## Schema Overview
Entities in `db/models.py`:
- `Site` — physical site (timezone, name)
- `Device` — device at a site (+ one-to-one `DeviceState`)
- `Point` — measurement point with `JSONB` tags and unit (unique per site+name)
- `PointMetadataHistory` — track historical metadata for points
- `Measurement` — time-series data with `measurement_timestamp`, `value`, `quality`, `unit`, and `meta_hash`
- `DeviceState` — heartbeat/health for devices (CPU, disk, status, last seen)

Timescale specifics applied by `init_db.py`:
- Primary key on `measurements (point_id, measurement_timestamp)`
- Hypertable: time column `measurement_timestamp`, space partition `point_id`, `number_partitions=8`
- Compression: order-by `measurement_timestamp DESC`, segment-by `point_id`
- Policies: compression after `COMPRESS_AFTER_DAYS`, retention after `RETAIN_DAYS`

See ERD diagram in `docs/db_erd.png`.

## Local Development (without Docker)
Prereqs: Python 3.11, PostgreSQL 15 with TimescaleDB extension installed and enabled on the target database.

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Set env vars for your local Postgres, then:
python init_db.py
```

## Migrations (Alembic)
Alembic is configured via `alembic.ini` and `migrations/`.

Typical commands:
```bash
# Generate a new revision after editing models
alembic revision -m "describe change"

# Apply migrations to the current database
alembic upgrade head
```

Note: `init_db.py` creates/aligns schema directly using SQLAlchemy metadata and Timescale helpers. Use Alembic for incremental evolution in real deployments.

## Troubleshooting
- Ensure the `timescaledb` extension is available: `CREATE EXTENSION IF NOT EXISTS timescaledb;`
- If policy or hypertable creation fails, verify the target table exists and the user has privileges.
- Windows line-endings warnings are harmless; Git may report CRLF/LF conversions.

## License
No license specified. Add a LICENSE file to clarify usage.

## Repository
GitHub: https://github.com/luqxcz/hvac-database
