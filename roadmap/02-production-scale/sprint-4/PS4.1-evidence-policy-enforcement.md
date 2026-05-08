# PS4.1 — Evidence policy expansion and enforcement

| Field | Value |
|-------|-------|
| **Task ID** | PS4.1 |
| **Status** | Todo |

---

## Description

Strengthen evidence-grounding rules so agent outputs cannot claim unsupported facts.
No invented citations; explicit fail-closed escalation when grounding quality is insufficient.

---

## Requirements

- [ ] Define enforceable evidence policy for report/plan claims and citation references.
- [ ] Add validation hook that rejects claims without evidence linkage.
- [ ] Ensure escalation reasons distinguish `no_evidence` vs `tool_failure` vs policy reject.
- [ ] Add low-cardinality observability fields for grounding outcomes.

---

## Checklist

- [ ] Policy documented in `docs/`.
- [ ] Unit tests for pass/fail policy paths.
- [ ] Existing pipeline tests updated to reflect stricter semantics.

---

## Test / acceptance

- [ ] At least one automated case fails on invented citation.
- [ ] At least one automated case passes with valid citation-grounded output.
- [ ] CI output includes clear failure reason for grounding violations.
