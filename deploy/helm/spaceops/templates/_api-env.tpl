{{- define "spaceops.apiEnv" -}}
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "spaceops.secretName" . }}
      key: {{ .Values.postgres.auth.secretKeys.password }}
- name: DATABASE_URL
  value: {{ include "spaceops.postgresUrl" . | quote }}
- name: OPA_URL
  value: {{ printf "http://%s-opa:%v/v1/data/agent/allow" (include "spaceops.fullname" .) .Values.opa.port | quote }}
- name: LLM_BACKEND
  value: {{ .Values.api.llm.backend | quote }}
- name: LLM_BUDGET_MODE
  value: {{ .Values.api.llm.budgetMode | quote }}
- name: GPU_ACTIVITY_FILE
  value: "/app/var/llm_last_gpu_call_at"
- name: AGENT_DURABLE_CHECKPOINT_ENABLED
  value: {{ .Values.api.checkpoint.enabled | quote }}
{{- if .Values.telemetryMcp.enabled }}
- name: TELEMETRY_MCP_URL
  value: {{ printf "http://%s-telemetry-mcp:%v/mcp" (include "spaceops.fullname" .) .Values.telemetryMcp.port | quote }}
{{- end }}
{{- if .Values.kbMcp.enabled }}
- name: KB_MCP_URL
  value: {{ printf "http://%s-kb-mcp:%v/mcp" (include "spaceops.fullname" .) .Values.kbMcp.port | quote }}
{{- end }}
{{- if .Values.ticketMcp.enabled }}
- name: TICKET_MCP_URL
  value: {{ printf "http://%s-ticket-mcp:%v/mcp" (include "spaceops.fullname" .) .Values.ticketMcp.port | quote }}
{{- end }}
{{- if .Values.gitopsMcp.enabled }}
- name: GITOPS_MCP_URL
  value: {{ printf "http://%s-gitops-mcp:%v/mcp" (include "spaceops.fullname" .) .Values.gitopsMcp.port | quote }}
{{- end }}
{{- if .Values.nats.enabled }}
- name: NATS_URL
  value: {{ printf "nats://%s-nats:%v" (include "spaceops.fullname" .) .Values.nats.port | quote }}
{{- end }}
{{- if .Values.observability.otelCollector.enabled }}
- name: OTEL_EXPORTER_OTLP_ENDPOINT
  value: {{ printf "http://%s-otel-collector:4317" (include "spaceops.fullname" .) | quote }}
{{- end }}
{{- if .Values.nim.enabled }}
- name: GPU_LLM_BASE_URL
  value: {{ printf "http://%s-nim:%v" (include "spaceops.fullname" .) .Values.nim.port | quote }}
{{- end }}
{{- range $key, $val := .Values.api.extraEnv }}
- name: {{ $key }}
  value: {{ $val | quote }}
{{- end }}
{{- end }}
