# Prompt injection threat model (PS4.3)

## Scope

Untrusted inputs that reach LLM prompts or tool-routing decisions:

| Source | Example risk |
|--------|----------------|
| Incident `payload` (operator/API) | Fake system instructions in `message` |
| KB runbook/postmortem snippets | Poisoned doc content from `evals/injection_suite`-style text |
| Telemetry-derived citation text | Less common; still scanned |
| Model-produced `plan` steps | Unsafe `action_type` or instruction-like `action` text |

## Threat classes (blocked)

1. **Policy bypass** — ignore/bypass OPA, skip approval, override policy.
2. **Execution** — run shell, execute command, `exec(`, `subprocess`, `os.system`.
3. **Role/instruction override** — fake `system:` roles, “ignore previous instructions”.
4. **Tool abuse** — `action_type` outside allowlist (`create_ticket`, `create_pr`, `change_config`, `restart_service`, `report`).

Stable escalation reason: `prompt_injection_detected`.

## Controls

| Control | Location |
|---------|----------|
| Pattern scan + severity | `apps/agent/prompt_injection.py` |
| Sanitize before prompt (`[BEGIN UNTRUSTED DATA]` fences) | `triage`, `decide` |
| Fail-closed escalation | `triage`, `check_escalation`, `decide`, `act` |
| Plan allowlist | `decide`, `act`; eval MoE3 via `evals/scoring.py` |
| Audit | `tool=prompt_injection_guard`, `args.detection_codes` |

## Observability

Spans may include `injection_guard_status`, `injection_guard_reason` (low cardinality).

## Verification

```bash
pytest tests/test_prompt_injection_ps43.py tests/test_evals.py -k injection -v
python -m evals.scoring  # injection suite: unsafe-action rate = 0
```

## Out of scope (follow-on)

- External LLM firewall (e.g. Lakera) — see `roadmap/02-production-scale.md`.
- Automatic KB quarantine UI — operators review audit + KB index.
