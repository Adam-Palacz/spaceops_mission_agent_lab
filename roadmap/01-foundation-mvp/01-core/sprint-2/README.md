# Sprint 2 — Act, approvals, OPA, injection suite, dashboards (Weeks 3–4)

**Goal:** Safe actions execute (ticket + GitOps PR); restricted require OPA allow + approval; approval API is idempotent and authenticated; fail-closed on OPA failure; injection suite + dashboards prove safety and observability.

---

## Outcomes

- MCP Ticketing (mock) and MCP GitOps (real PR to ops-config).
- Decide: steps tagged safe vs restricted; Act executes safe only; restricted → OPA → if allow, approval request; if OPA down/timeout/error → deny + escalation (NF8).
- Approval API: idempotent approve/reject; AuthN (API key/token); audit who approved and when (NF9).
- Audit log includes approval events (actor=human).
- Injection suite: 5–10 KB docs; evals require unsafe-action rate = 0.
- Prometheus metrics + Grafana dashboard.

---

## Tasks

See **[BOARD.md](BOARD.md)** for status. Each task has a detail file: `S2.x-short-name.md`. Unit tests in **tests/** are expanded in **S2.11** (approval API, OPA client, Act; S2.10 covers OPA policy Rego tests).

---

## Definition of done (sprint)

- [ ] Safe actions create ticket and PR; restricted go through OPA → allow → approval → execution; OPA failure → deny + escalation.
- [ ] Approval endpoints idempotent and auth’d; audit records who/when.
- [ ] Injection suite in CI; unsafe-action rate = 0 required.
- [ ] Metrics and dashboard show run count, latency, tool-call count.
- [ ] Unit tests in **tests/** for approval API, OPA client, and fail-closed behaviour; pytest in CI.

---

## Instructions for AI

- Implement in order S2.1 → S2.11 where possible; S2.3–S2.6 depend on S2.1–S2.2 and S2.4 (OPA); S2.11 adds unit tests for S2 scope.
- For each task: open `S2.x-*.md`, follow Requirements and Checklist, run Test requirements, then set status to Done in BOARD.md.
- Do not change task scope without updating the task .md and BOARD.
