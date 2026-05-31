{{/*
Expand the name of the chart.
*/}}
{{- define "spaceops.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "spaceops.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "spaceops.namespace" -}}
{{- .Values.global.namespace | default .Release.Namespace }}
{{- end }}

{{- define "spaceops.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "spaceops.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "spaceops.selectorLabels" -}}
app.kubernetes.io/name: {{ include "spaceops.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "spaceops.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "spaceops.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "spaceops.componentServiceAccountName" -}}
{{- $root := .root -}}
{{- $component := .component -}}
{{- if and $root.Values.isolation.enabled $root.Values.isolation.workloadServiceAccounts }}
{{- printf "%s-%s" (include "spaceops.fullname" $root) $component | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- include "spaceops.serviceAccountName" $root }}
{{- end }}
{{- end }}

{{- define "spaceops.image" -}}
{{- $repo := .repository -}}
{{- $tag := .tag | default "latest" -}}
{{- printf "%s:%s" $repo $tag -}}
{{- end }}

{{- define "spaceops.postgresHost" -}}
{{- printf "%s-postgres" (include "spaceops.fullname" .) }}
{{- end }}

{{- define "spaceops.postgresUrl" -}}
{{- $user := .Values.postgres.auth.username -}}
{{- $db := .Values.postgres.auth.database -}}
{{- $host := include "spaceops.postgresHost" . -}}
{{- $port := .Values.postgres.port -}}
{{- printf "postgresql://%s:$(POSTGRES_PASSWORD)@%s:%v/%s" $user $host $port $db -}}
{{- end }}

{{- define "spaceops.secretName" -}}
{{- if .Values.secrets.existingSecret -}}
{{- .Values.secrets.existingSecret -}}
{{- else if .Values.postgres.auth.existingSecret -}}
{{- .Values.postgres.auth.existingSecret -}}
{{- else if .Values.secrets.create -}}
{{- .Values.secrets.name | default (printf "%s-secrets" (include "spaceops.fullname" .)) -}}
{{- else -}}
{{- fail "secrets: set secrets.create=true, secrets.existingSecret, or postgres.auth.existingSecret" -}}
{{- end -}}
{{- end }}
