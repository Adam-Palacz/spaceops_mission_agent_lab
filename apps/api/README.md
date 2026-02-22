# SpaceOps API

FastAPI app: health, ingest (NDJSON), run trigger (stub).

## Run

From repo root (with deps installed: `pip install -r requirements.txt`):

```bash
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

- **GET** http://localhost:8000/health → 200
- **POST** http://localhost:8000/ingest?source=telemetry — body: NDJSON (one JSON object per line)
- **POST** http://localhost:8000/runs — body: JSON `{"incident_id": "inc-1", "payload": {}}` → 202 (stub)

## Ingest

Query param `source` must be one of: `telemetry`, `events`, `ground_logs`.  
Data is written under `data/{source}/ingest_{timestamp}.ndjson`.
