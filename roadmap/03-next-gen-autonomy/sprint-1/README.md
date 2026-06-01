# NG1 — Multi-agent foundation (Theme 1)

**Goal:** hierarchical LangGraph with **Flight Director (supervisor)** and at least two
**specialist agents** (Power, Thermal), preserving audit and OPA per proposed action.

**Outcomes**

- ADR: routing supervisor → 1..N specialists → merge Plan/Report.
- Two specialists with narrow prompts and subsystem-scoped tools.
- Trace/audit shows which agent produced which fragment.
- Eval: power-related incident engages Power agent (fixture).

**Definition of done**

- [ ] Locally (`compose` or `k8s-up` minimal): multi-agent run for power + thermal crossover fixture.
- [ ] No OPA bypass for restricted actions.
- [ ] Docs in `docs/` + portfolio update (L3 section).

See [BOARD.md](BOARD.md).
