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
# CI-equivalent check (mocked fixture + any other tests)
make golden-check

# Optional: replay real pinned runs (needs MCP/.env/OpenAI like normal replay)
python scripts/golden_baseline.py check \
  --manifest data/replay/golden/manifest.json \
  --baselines-dir data/replay/golden/baselines

# Refresh one baseline after intentional behavior change (requires successful replay)
python scripts/golden_baseline.py update --run-id '<uuid>'
```

Exit codes for `golden_baseline.py check`: `0` = match, `2` = mismatch, `1` = error.

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
