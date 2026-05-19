# Golden-run baselines (PS2.8)

Pinned **replay outcomes** for selected `run_id`s. Use them to catch regressions in triage,
escalation, and citations when prompts, models, or guardrails change.

This doc complements [Replay metadata](replay_metadata.md) (PS1.4) and the
[Replay workflow runbook](runbooks/replay_workflow.md) (PS1.5): metadata stores *what ran*;
golden baselines store *approved comparison fields* for those runs.

## Layout and naming

| Path | Purpose |
|------|---------|
| `data/replay/golden/manifest.json` | `golden_manifest_v1` — list of pinned `run_id`s under `cases[]`. |
| `data/replay/golden/baselines/run_<run_id>_baseline.json` | `golden_baseline_v1` — `expected_outcome` for that run. |

CI uses an **in-repo synthetic** pin under `tests/fixtures/golden/` (same schema) so checks do not
call live LLMs. Optional real `run_id`s live only in `data/replay/golden/` when your team adds them.

`<run_id>` in the filename must match the replay metadata filename (`data/replay/runs/<run_id>.json`;
that directory is often gitignored — export or regenerate metadata when adding a pin).

## Fields compared

Baselines compare the **replay** pipeline output against `expected_outcome`. Each key in
`expected_outcome` must be one of:

- `subsystem` — string  
- `escalated` — boolean  
- `has_citations` — boolean (any `citations` or `report.citation_refs`)  
- `escalation_reason` — string, `report.escalation_packet.reason` (or top-level `escalation_packet`)  
- `citation_count` — non-negative int: `len(citations)` if present, else `len(citation_refs)`

The same five fields are used in the [replay API/UI diff](runbooks/replay_workflow.md) between
original and replay outcomes; baselines pin the **expected replay** snapshot.

You may omit keys in `expected_outcome` that you do not want to enforce; only listed keys are checked.

## Commands (repo root)

```bash
# CI-equivalent check (mocked fixture + PS4.5 runner tests)
make golden-check

# PS4.5: run fixture set + write machine-readable diff report (no live LLM for CI manifest)
make golden-run
# → data/replay/golden/reports/latest/report.json
# → data/replay/golden/reports/latest/cases/<case_id>_diff.json

# Check with diff artifacts on failure
python scripts/golden_runner.py check \
  --manifest tests/fixtures/golden/manifest.json \
  --baselines-dir tests/fixtures/golden/baselines \
  --output-dir data/replay/golden/reports/latest

# Optional: replay real pinned runs (needs MCP/.env/OpenAI like normal replay)
python scripts/golden_runner.py check \
  --manifest data/replay/golden/manifest.json \
  --baselines-dir data/replay/golden/baselines

# Refresh baseline — requires explicit operator confirm (PS4.5)
python scripts/golden_runner.py update --run-id '<uuid>' --confirm baseline-update
```

Exit codes for `golden_runner.py` / `golden_baseline.py check`: `0` = match, `2` = mismatch, `1` = error.

## PS4.5 — Golden runner and diff artifacts

| Artifact | Schema | Purpose |
|----------|--------|---------|
| `report.json` | `golden_diff_report_v1` | Suite summary + per-case status |
| `cases/<case_id>_diff.json` | — | Semantic field diffs only |
| `cases/<case_id>_snapshot.json` | — | Expected vs replay outcome snapshots |

Manifest cases may set `replay_fixture` to a JSON path (relative to manifest dir) for
**deterministic** runs without calling the live pipeline — used by `tests/fixtures/golden/`.

### Check vs update policy

| Action | When | Command |
|--------|------|---------|
| **Check** | Every PR / release gate | `make golden-check` or `golden_runner check` |
| **Update** | Intentional model/prompt/guardrail change | `golden_runner update --confirm baseline-update` |

Never refresh baselines to silence flakes; fix determinism or update with documented intent.

## Update policy

1. **Intentional model/prompt/KB change** — replay the golden `run_id`, confirm the new behavior,
   then run `golden_baseline.py update --run-id …` and commit the baseline + manifest entry.
2. **Regression** — `golden-check` / `pytest tests/test_golden_baseline.py` fails; fix code or argue
   why the baseline must move (then update per (1)).
3. Do not edit baselines to silence flakes — fix determinism (fixtures, temperature=0, MCP mocks).

See also [evals README](../evals/README.md) for how golden checks relate to eval cases.

## PR checklist

Before merge when replay-related code changes:

- [ ] `make golden-check` (or full `pytest tests/`) passes.  
- [ ] If behavior intentionally changed: baselines/manifest updated and noted in the PR description.

## Link: PS1.5

Replay execution and CLI/API semantics: [runbooks/replay_workflow.md](runbooks/replay_workflow.md).
