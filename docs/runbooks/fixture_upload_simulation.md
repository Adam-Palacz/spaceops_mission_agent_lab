# Fixture upload + simulate run (PS2.7)

Operators can upload a **small incident-shaped JSON** via **`POST /runs/simulate`** or the **Simulate** page in SpaceOps UI to run the agent pipeline without reusing a production `incident_id`.

On **`/simulate`**, **Formularz** sends **`POST /runs/simulate/quick`** with required selects (`scenario_ref`, `subsystem_hint`, `risk_level`, ISO time window); the API builds **`payload`** via **`SimulateQuickFormPayload`** (Pydantic **422** if anything is missing or invalid). **Upload** still uses **`POST /runs/simulate`** with a JSON file (`incident_id` + `payload`).

## Behaviour

- **Fixture shape:** one JSON object with **`incident_id`** (string) and **`payload`** (object). Same logical input as `POST /runs`, but the pipeline is invoked with a synthetic id: **`sim-upload-<10 hex>-<slug>`** derived from the declared `incident_id`, so list/detail views are clearly distinct from production runs.
- **Persisted run file** includes **`simulation": true`**, **`source_fixture_incident_id`** (declared id from the file), and optional **`fixture_upload_name`** (sanitized basename only).
- **Size limit:** 48 KiB UTF-8 text. **Format:** JSON object only (not NDJSON batches; use **`POST /ingest`** for telemetry NDJSON, then **`POST /runs`** if needed).
- **List filter:** `GET /runs?simulation=true` / `simulation=false` (PS2.7).

## Threat model (MVP)

| Risk | Mitigation |
|------|------------|
| Path traversal in filename | Only **`Path(filename).name`** is stored; no path segments written to disk from the client name. |
| Huge uploads | Hard **byte cap** (413). |
| Binary / non-UTF-8 | Reject non-UTF-8 decode; JSON parse required. |
| XSS via uploaded JSON rendered in UI | UI treats content as **data** (no `dangerouslySetInnerHTML`); operator JSON is shown in `<pre>` / text nodes only. |
| Malware in file | **Out of scope** for MVP (no AV scan); trusted local/dev use only. |

## Auth / exposure

Same network exposure as **`POST /runs`** (no extra API key in MVP). For anything beyond trusted local/dev, put the API behind a gateway with **auth and rate limits** (called out in PS2.7 roadmap).

## See also

- Operator UI: **`/simulate`** (Next.js).
- Normal run trigger: **`POST /runs`**.
