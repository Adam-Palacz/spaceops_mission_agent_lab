{{- define "spaceops.secretEnvOptional" -}}
{{- $root := index . 0 -}}
{{- $envName := index . 1 -}}
{{- $key := index . 2 -}}
- name: {{ $envName }}
  valueFrom:
    secretKeyRef:
      name: {{ include "spaceops.secretName" $root }}
      key: {{ $key }}
      optional: true
{{- end }}
