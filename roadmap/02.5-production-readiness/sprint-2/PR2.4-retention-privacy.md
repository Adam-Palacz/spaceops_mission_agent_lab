# PR2.4 - Trace/log retention and privacy policy

## Description

Define how traces, logs, audit records, metrics, eval artifacts, and reports are retained and what
data may be exported to external providers. This prepares NG3 compliance work and production pilot
review.

## Requirements

- Retention policy for traces, logs, metrics, audit, approvals, eval reports, and generated reports.
- Privacy/data classification for simulated, stage, and production-pilot data.
- Redaction requirements for logs, traces, prompts, audit args, and reports.
- Managed trace/log backend decision plus minimum implementation path for production pilot
  (for example Cloud Trace, Grafana Tempo, persistent Jaeger, or an accepted temporary stage-only
  alternative with explicit retention limits).
- Deletion/export process for operator review artifacts.

## Checklist

- [ ] Retention matrix added.
- [ ] Data classification matrix added.
- [ ] Redaction expectations documented.
- [ ] Trace/log backend decision and minimum implementation path documented.
- [ ] NG3 compliance dependency noted.

## Test requirements

- Static checks or tests for known sensitive fields where available.
- Documentation link test.
