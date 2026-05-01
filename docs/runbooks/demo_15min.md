# 15-minute demo script (MVP) — with optional `.env` skip

Use this script to show the project end-to-end in one short session: run stack, ingest data, trigger agent, inspect output, and explain why it is safe.

---

## 0) Preconditions

- You run commands from repo root.
- Docker Desktop is running.
- Python deps are installed (`pip install -r requirements.txt`).
- You already have valid LLM credentials available.

---

## 1) Environment setup (choose one)

### Option A — skip `.env` setup (if you already have it)

If your `.env` already exists and works, skip this section entirely and go to step 2.

### Option B — first-time setup

1. Copy `.env.example` to `.env`.
2. Set at least:
   - `OPENAI_API_KEY=...`
3. Optional for approvals:
   - `APPROVAL_API_KEY=demo-key`

---

## 2) Start local stack (2-3 min)

```powershell
docker compose -f infra/docker-compose.yml --project-directory . up -d
```

This starts API + Postgres + OPA + MCP servers (`telemetry`, `kb`, `ticket`, `gitops`).
Quick check:

```powershell
docker compose -f infra/docker-compose.yml --project-directory . ps
```

Optional (legacy mode): if you prefer API outside Docker, run:

```powershell
python -m apps.api.main
```

Then keep API running in that terminal and use a second terminal for demo calls.

---

## 3) Health + ingest (2 min)

### Health check

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
```

Expected: status ok.

### Ingest fixture

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/ingest?source=telemetry" `
  -ContentType "application/x-ndjson" `
  -InFile "data/telemetry/telemetry.ndjson"
```

Expected: API confirms accepted rows and writes ingest file under `data/telemetry/`.

---

## 4) Trigger one incident run (3-4 min)

```powershell
$body = @{
  incident_id = "inc-demo-1"
  payload = @{
    time_range_start = "2025-02-14T09:00:00Z"
    time_range_end   = "2025-02-14T11:00:00Z"
    message          = "Demo anomaly triage run"
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/runs" `
  -ContentType "application/json" `
  -Body $body
```

Expected:
- run accepted/executed,
- report fields include triage/investigation/decision context,
- restricted actions (if any) are gated by policy/approval flow, not silently executed.

---

## 5) Show why this is safe (2-3 min)

Run:

```powershell
python -m evals.scoring
```

Explain:
- evals include standard cases + injection suite,
- CI gates regressions,
- unsafe-action rate must remain 0.

Optional model lifecycle demo:

```powershell
python -m evals.shadow_models
```

Explain:
- compares production model vs candidates,
- writes JSON report in `evals/reports/`,
- promotion decision is evidence-based.

---

## 6) Talk track: "what happens and why" (60-90 sec)

- **MCP boundary only:** agent does not execute shell; tools are explicit servers.
- **Policy first:** restricted actions require OPA allow; failures are fail-closed.
- **Human control:** approvals are authenticated and auditable.
- **Quality gates:** evals + injection suite enforce behavioural safety.
- **Observability:** traces/metrics/audit explain each run after the fact.

---

## 7) Quick troubleshooting

- `connection refused` on API: verify `python -m apps.api.main` is running.
- Postgres/vector errors: ensure compose stack is up before KB/index/evals.
- Evals fail unexpectedly: verify `OPENAI_API_KEY`, OPA/MCP availability, and network.
- Approval endpoints 401/403: check `APPROVAL_API_KEY`.

---

## 8) Cleanup

Stop API with `Ctrl+C`, then:

```powershell
docker compose -f infra/docker-compose.yml down
```

---

*Tip: for live presentations, keep one terminal with API logs and one with commands/results; it makes the "why" explanation much easier.*
