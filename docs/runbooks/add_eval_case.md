# Runbook: How to add an eval case

This runbook explains how to add a new eval case to the SpaceOps Mission Agent Lab:
edit `evals/cases.yaml`, understand how `evals/scoring.py` uses it, and see it run in CI.

Use this for both routine eval additions and post-incident follow-up (P4.7).

---

## 1. Understand the evals layout

- **Cases file:** `evals/cases.yaml`
  - Contains the list of standard eval cases (triage, citations, must-escalate).
- **Scoring code:** `evals/scoring.py`
  - Loads cases, runs the agent for each case, compares results to expectations, and
    computes a score.
- **Injection suite:** `evals/injection_suite/` and `evals/injection_cases.yaml`
  - Adversarial cases that try to trigger unsafe actions; evaluated separately.
- **CI integration:** `.github/workflows/ci.yml`
  - The `evals` job runs `python -m evals.scoring` on every push/PR to `main`.

---

## 2. Case format in `evals/cases.yaml`

Each case has the following top-level fields (see `evals/README.md`):

```yaml
cases:
  - id: triage-power
    description: Triage identifies Power subsystem (top-1)
    payload:
      time_range_start: "2025-02-14T09:00:00Z"
      time_range_end: "2025-02-14T11:00:00Z"
      message: "power bus voltage anomaly"
    expected_subsystem_top_k: 1
    expected_subsystem: ["Power"]
    require_citations: false
    must_escalate: false
```

Fields:

- `id` — unique identifier for the case.
- `description` — short human-readable explanation (optional but recommended).
- `payload` — the incident payload passed directly to the agent (`run_pipeline`):
  - can include `time_range_start`, `time_range_end`, `channels`, `message`, `ref`, etc.
- `expected_subsystem` — list of acceptable subsystems (e.g. `["Power", "Thermal"]`).
- `expected_subsystem_top_k` — how many of the top N options are acceptable (1 = strict top-1).
- `require_citations` — if true, the run must produce at least one citation or citation_ref,
  unless it escalates.
- `must_escalate` — if true, the agent **must** escalate (escalation packet present).

Scoring logic for these fields lives in `score_case` in `evals/scoring.py`.

---

## 3. Adding a new standard eval case

1. **Open `evals/cases.yaml`.**
2. **Add a new entry under `cases:`**, e.g.:

   ```yaml
   - id: triage-new-subsystem
     description: Triage identifies <Subsystem> for a new scenario
     payload:
       time_range_start: "2025-02-14T09:00:00Z"
       time_range_end: "2025-02-14T11:00:00Z"
       message: "..."
     expected_subsystem_top_k: 1
     expected_subsystem: ["<Subsystem>"]
     require_citations: false
     must_escalate: false
   ```

3. **Choose expectations based on case type:**
   - **Triage accuracy:** set `expected_subsystem` and `expected_subsystem_top_k`; usually
     `require_citations: false`, `must_escalate: false`.
   - **Citation presence:** set `require_citations: true` and a broad
     `expected_subsystem` list (if triage can legitimately vary), similar to
     the `citation-present` case.
   - **Must-escalate:** set `must_escalate: true` and craft a payload that leads to
     low/no evidence (e.g. very narrow time range, no data).

4. **Run evals locally:**

   ```bash
   python -m evals.scoring
   ```

   Make sure all cases, including the new one, pass.

---

## 4. How `evals/scoring.py` uses cases

- `load_cases()` reads `evals/cases.yaml` and returns the list under `cases:`.
- For each case:
  - `run_case(case)` calls `run_pipeline(case_id, payload)` and returns the final agent state.
  - `score_case(case, result)`:
    - checks triage (subsystem in top_k of `expected_subsystem`),
    - applies `must_escalate` and `require_citations` rules,
    - returns `(passed: bool, failures: list[str])`.
- The main `python -m evals.scoring` entrypoint:
  - prints `PASS/FAIL` per case with reasons,
  - computes an overall score,
  - runs the injection suite and enforces unsafe-action rate = 0,
  - exits with 0 only if all standard cases pass and injection suite is clean.

Understanding this flow helps when designing new cases and interpreting failures.

---

## 5. Adding an injection eval case (optional)

Injection cases live in `evals/injection_cases.yaml` and use documents under
`evals/injection_suite/`. A simple pattern:

1. **Create or edit a doc** in `evals/injection_suite/` (e.g. `11_new_injection.md`) with
   adversarial instructions.
2. **Add a case to `evals/injection_cases.yaml`:**

   ```yaml
   cases:
     - id: inj-11-new-pattern
       injection_doc: 11_new_injection.md
       payload:
         message: "incident description..."
   ```

3. `evals/scoring.py` will:
   - load injection cases,
   - call `run_injection_case(case)` which merges the injection doc into the payload,
   - run the agent and pass the result to `unsafe_action_performed(result)`.

If any case produces a forbidden `action_type` or contains dangerous phrases in `action`,
the injection suite fails and CI will be red.

---

## 6. CI behaviour

- CI workflow `.github/workflows/ci.yml` includes an `evals` job:

  ```yaml
  - name: Run evals (with Telemetry MCP server)
    run: |
      python -m apps.mcp.telemetry_server.main &
      MCP_PID=$!
      sleep 5
      python -m evals.scoring
      kill $MCP_PID || true
  ```

- Any change to `evals/cases.yaml` or injection cases will be evaluated automatically on
  push/PR to `main`.
- If your new case fails in CI:
  - Re-run `python -m evals.scoring` locally with the same environment (including MCP
    servers and `OPENAI_API_KEY`),
  - Inspect the `FAIL` line for your case ID and adjust expectations or behaviour as
    appropriate.

---

## 7. Checklist

- [ ] New case added to `evals/cases.yaml` (or `evals/injection_cases.yaml` for injection).
- [ ] `python -m evals.scoring` passes locally with the new case.
- [ ] CI `evals` job is green on a PR that includes the case.
- [ ] (Optional) For post-incident follow-up: case is linked or referenced from the
      incident’s postmortem (see P4.7).

