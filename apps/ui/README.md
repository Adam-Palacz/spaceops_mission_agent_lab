# SpaceOps UI (Next.js) — P4.5

Minimal operator UI for:
- incident/run list (`GET /runs`)
- approval list (`GET /approvals`)
- approval actions (`POST /approvals/{id}/approve|reject`)

## Prerequisites

- Node.js 20+
- Running API (`python -m apps.api.main` on `http://localhost:8000`)
- `APPROVAL_API_KEY` set for the backend (same key used by UI)

## Configure

Copy env file:

```bash
cp .env.example .env.local
```

Set values:

- `NEXT_PUBLIC_API_BASE_URL` (default: `http://localhost:8000`)
- `NEXT_PUBLIC_APPROVAL_API_KEY` (must match backend `APPROVAL_API_KEY`)

## Run

```bash
npm install
npm run dev
```

Open: `http://localhost:3001`

## Run in Docker

From repo root (starts both `api` and `ui` services under profile `ui`):

```bash
docker compose -f infra/docker-compose.yml --project-directory . --profile ui up -d --build api ui
```

The UI service uses build args:

- `UI_API_BASE_URL` (defaults to `http://localhost:8000`)
- `APPROVAL_API_KEY` (reused from backend auth)

Open: `http://localhost:3001`

API health: `http://localhost:8000/health`

## Notes

- This is an MVP operator UI, intentionally simple and local-first.
- `NEXT_PUBLIC_APPROVAL_API_KEY` is exposed to the browser; use only in trusted local/dev environments.
- For Docker, the same key is baked at build time via `APPROVAL_API_KEY`; rebuild when the key changes.
