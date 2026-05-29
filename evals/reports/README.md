# Shadow model reports (P4.8)

`python -m evals.shadow_models` writes timestamped JSON files here:

- `shadow_models_YYYYMMDDTHHMMSSZ.json` — full comparison (baseline + candidates).

These generated files are **gitignored** so local runs do not clutter commits. In CI, the
**Shadow models** workflow uploads the latest file as a workflow artifact.

For the report schema and how to interpret results, see [docs/shadow_models.md](../../docs/shadow_models.md).

A **static example** (shape only, not from a live run) is [sample_shadow_report.json](sample_shadow_report.json).

**PS5.8 backend parity:** [sample_backend_parity_report.json](sample_backend_parity_report.json) —
see [docs/evals_backend_parity.md](../../docs/evals_backend_parity.md). Generated
`backend_parity_*.json` files are gitignored.
