# Runbook: Post-incident learning loop (P4.7)

This runbook defines what to do after closing a significant incident so the system learns:

1. Add/update postmortem in `kb/postmortems/`
2. Re-index KB vectors
3. Add at least one eval case
4. Run evals and push (CI gate)

---

## 1) Add postmortem

- Create a new file in `kb/postmortems/`, e.g.:
  - `kb/postmortems/2026-04-thermal-heater-loop.md`
- Use the template:
  - `kb/postmortems/_template.md`
- Ensure the **Signature** section includes practical retrieval keywords.

---

## 2) Re-index KB (runbooks + postmortems)

From repo root:

```bash
python -m scripts.reindex_kb
```

Equivalent direct command:

```bash
python -m apps.mcp.kb_server.index_kb
```

Expected output includes:
- number of indexed chunks
- number of source documents

If it fails:
- verify `OPENAI_API_KEY`
- verify Postgres (`POSTGRES_*` or `DATABASE_URL`)
- ensure pgvector schema exists (script auto-creates table/index)

---

## 3) Add eval case (mandatory for significant incidents)

- Add at least one case to `evals/cases.yaml` or `evals/injection_cases.yaml` (if security/adversarial).
- Follow:
  - `docs/runbooks/add_eval_case.md`

Recommended:
- one case reproducing the incident signature
- one case checking expected escalation/guardrail behavior (if relevant)

---

## 4) Validate locally and in CI

Run locally:

```bash
python -m evals.scoring
```

Then push PR/commit so CI runs evals as a required check.

---

## Quick checklist

- [ ] Postmortem added/updated in `kb/postmortems/`
- [ ] KB re-index completed successfully
- [ ] New eval case added
- [ ] `python -m evals.scoring` passes locally
- [ ] Changes pushed; CI evals green

