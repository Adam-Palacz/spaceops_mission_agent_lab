# DB migrations runbook

Migration baseline for PS1.3 uses Alembic and contract-aligned tables:
`telemetry_events`, `incidents`, `runs`, `audit_log`.

## Prerequisites

- Postgres reachable from your environment.
- `POSTGRES_*` in `.env` or `DATABASE_URL` set.
- Dependencies installed: `pip install -r requirements.txt`.

## Configure DB URL

Alembic resolves DB URL in this order:

1. `ALEMBIC_DATABASE_URL`
2. `DATABASE_URL`
3. `POSTGRES_*` composed from `config.settings.postgres_dsn`

Example:

```powershell
$env:ALEMBIC_DATABASE_URL="postgresql://spaceops:example_password@localhost:5432/spaceops"
```

## Run migrations

- Upgrade to latest:

```powershell
python -m alembic upgrade head
```

- Show current revision:

```powershell
python -m alembic current
```

- Downgrade one step:

```powershell
python -m alembic downgrade -1
```

- Full reset to baseline (destructive for migrated objects):

```powershell
python -m alembic downgrade base
python -m alembic upgrade head
```

## Append-only guarantees

- `telemetry_events` and `audit_log` are protected by DB triggers.
- Any `UPDATE` or `DELETE` on those tables raises an exception.
- Only `INSERT` is allowed (append-only semantics).

## CI migration smoke

CI validates migration flow on clean DB:

1. `alembic upgrade head`
2. `alembic downgrade base`
3. `alembic upgrade head`

This catches broken revisions and downgrade drift early.
