# SpaceOps Mission Agent Lab — Phase 8 / Next-Gen Autonomy (L3–L4)

**Purpose:** extend SpaceOps from L1/L2 automation (MVP + productionisation) to **L3/L4 autonomy**
that would be credible for agencies and operators (ESA/NASA, commercial constellations). This
phase is **not** for current delivery; it is a forward-looking design for:

- Hierarchical, multi-agent “Flight Director” patterns,
- richer human–AI collaboration in planning,
- compliance-aware data handling (e.g. ITAR/EAR),
- edge autonomy with air‑gapped SLMs,
- and next‑gen knowledge retrieval (GraphRAG).

Use this file as a **vision/backlog**; concrete work should be pulled into future sprints or
dedicated phases once core and production-scale milestones are stable.

---

## Autonomy Levels (context)

- **L1/L2 (current roadmap):** single agent pipeline, evidence-grounded reporting, safe Act with
  OPA + approvals, observability and eval gates.
- **L3 (assisted autonomy):** multiple specialised agents coordinated by a Flight Director;
  advanced human-in-the-loop where operator edits and steers plans; system handles connectivity
  loss and degraded modes.
- **L4 (supervised autonomy):** agents proactively coordinate across subsystems with rich models
  of failure modes (GraphRAG); offline-capable local models; strong compliance and data-masking
  baked into the architecture.

This document sketches what L3/L4 could look like in SpaceOps.

---

## Theme 1 — Multi-Agent Architecture (“Flight Director” Pattern)

**Problem:** A single monolithic agent is responsible for Power, Thermal, ADCS, Comms, Ground, etc.
As the system grows, prompts become unwieldy and risk hallucinations/missed interactions.

**Concept:** Hierarchical, multi-agent LangGraph with a **Flight Director Agent (Supervisor)**
and multiple **specialist agents**:

- Flight Director:
  - classifies incident type and criticality,
  - decides which specialist agents to involve (Power, Thermal, ADCS, Comms, Ground),
  - aggregates their findings into a coherent plan and report.
- Specialist agents:
  - operate on subsystem-specific telemetry/KB,
  - have tailored prompts and tools (e.g. Power Agent knows about bus voltage, battery SoC;
    Thermal Agent about heaters, radiators, thermal limits),
  - return structured findings (hypotheses, risks, recommended actions).

**Backlog ideas:**

- Design a **Supervisor graph** that:
  - routes incidents to 1–N subsystem agents,
  - merges their outputs into a final Plan/Report node,
  - preserves per-agent audit and traceability.
- Define initial **specialist agents**:
  - Power Agent,
  - Thermal Agent,
  - ADCS Agent,
  - (optionally) Comms/Ground Agent.
- Ensure escalation and OPA/approval flows still apply per action, regardless of which agent
  proposed it (policy before execution).

---

## Theme 2 — Advanced Human-in-the-Loop (Collaborative Planning)

Current roadmap (S2 + Phase 4) focuses on **Approve/Reject** semantics for plans and actions.
For mission ops, this should evolve into **collaborative planning**:

- Operators can:
  - edit, reorder, or annotate the agent’s plan before approval,
  - provide explicit feedback (e.g. “sensor A is known-bad, trust sensor B more”),
  - request “replan” under new constraints.
- The agent:
  - treats human edits as **constraints** and **feedback signals**,
  - updates its internal state/prompt context accordingly,
  - re-runs Decide/Act under operator guidance.

**Backlog ideas:**

- Extend the approval API/UX to support:
  - editing of plan steps (text + metadata) and sending them back into LangGraph as updated state,
  - structured operator feedback objects (e.g. “deprioritise source X”, “avoid subsystem Y”).
- Add a **“replan with human constraints”** node in the graph that:
  - reuses evidence/hypotheses,
  - incorporates operator constraints,
  - preserves audit trail of which parts were human-authored vs agent-generated.
- Surface this in UI (Phase 1/Hardening) so ops can see *why* the agent changed the plan.

---

## Theme 3 — Data Masking & Compliance (ITAR/EAR-Aware Gateway)

Space ops are subject to export and data-handling regulations (e.g. ITAR/EAR). Sending raw
telemetry, orbital parameters, or sensitive subsystem names to a public LLM API is a legal and
security risk.

**Concept:** Introduce a **Confidentiality/PII Scrubber Gateway** in front of the LLM Gateway:

- Detects and **redacts or tokenises** sensitive fields before they leave the operator’s trust
  boundary (e.g. before calling OpenAI/Anthropic).
- Replaces sensitive values with stable placeholders (`<REDACTED_ORBITAL_PARAM>`,
  `<REDACTED_KEY>`, etc.).
- Maintains a reversible mapping within the secure environment (for internal logs/KB only),
  but never leaks originals to external providers.

**Backlog ideas:**

- Evaluate tools/approaches:
  - rule-based masking for known fields (satellite IDs, TLEs, key material),
  - NER-based scrubbers (e.g. Presidio-like) for less structured text.
- Design a **redaction policy**:
  - what must always be removed,
  - what may be coarsened (e.g. “LEO orbit” vs exact orbital elements),
  - what can pass through unchanged.
- Integrate the scrubber into the **LLM Gateway** so every outbound prompt goes through it,
  with:
  - explicit configuration of policies per environment,
  - audit logging of masking decisions (without leaking secrets).

---

## Theme 4 — Edge Autonomy & Air-Gapped SLMs

Ground stations and some mission control setups operate with constrained or unreliable internet
connectivity. For safety and continuity, the system should **continue to function in a degraded
but safe mode** when cloud LLMs are unavailable.

**Concept:** Dual-mode LLM Gateway:

- **Online mode:** uses cloud LLMs (OpenAI, etc.) as in Phase 5.
- **Offline/edge mode:** falls back to local **Small/Medium Language Models (SLMs)** (e.g. 7B–14B,
  quantised) running on local GPU/CPU in an air-gapped environment.

**Backlog ideas:**

- Extend the LLM Gateway to:
  - detect connectivity/cloud availability,
  - switch between cloud and local models with a clear **capability/limitations profile**,
  - expose which backend was used for each run (for audit + evals).
- Evaluate and prototype local models (e.g. Llama 3 8B, Mistral) with:
  - quantisation strategies (GGUF/AWQ),
  - resource requirements compatible with typical ground-station hardware.
- Define behaviour under offline mode:
  - which features degrade (e.g. smaller context, less fluent language),
  - which guarantees must still hold (NF6, NF8, escalation rules).

---

## Theme 5 — Next-Gen RAG: GraphRAG & Hybrid Search

Current KB design relies on vector search (pgvector) over runbooks/postmortems. As the system
grows, this risks missing **structured relationships** (e.g. power failure causing thermal
issues, which then affect propulsion).

**Concept:** Augment RAG with **GraphRAG + hybrid search**:

- Represent subsystem relationships and failure modes in a **knowledge graph** (e.g. Neo4j).
- Combine:
  - symbolic/graph traversal (find related components, failure chains),
  - semantic vector search for relevant documents/snippets.

**Backlog ideas:**

- Model a minimal **spacecraft dependency graph**:
  - nodes: subsystems, components, failure modes,
  - edges: “feeds”, “cools”, “depends on”, “shares bus with”, etc.
- On incident:
  - use graph traversal to identify which subsystems and components are likely involved,
  - use vector search only within the **graph neighbourhood** to retrieve focused runbooks.
- Update evals to test “multi-hop” reasoning:
  - scenarios where a single symptom (e.g. “panel stuck”) should trigger checks in multiple
    subsystems via the graph structure.

---

## How to use this document

- **Do not pull these themes into S1/S2**; they belong to **post-MVP / production-scale** work
  and should be scheduled once core reliability and safety are proven.
- When planning future phases/sprints, map concrete backlog items here into:
  - new sprint tasks (e.g. under a future “E3 — Next-Gen Autonomy” epic),
  - or into dedicated hardening/innovation tracks.
- Keep this file aligned with:
  - `01-foundation-mvp.md` (core),
  - `02-production-scale.md` (productionisation),
  - `post-mvp.md` (longer-term roadmap),
  - and `base-roadmap.md` (overview).

