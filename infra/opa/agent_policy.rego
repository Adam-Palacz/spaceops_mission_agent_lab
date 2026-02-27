package agent

# Default: deny everything (fail-closed). S2.4, NF8.
default allow = false

# Allowlist of restricted action types that can ever be considered for approval.
allowed_action_types := {"change_config", "restart_service"}

# Deny obviously dangerous phrases in free-text actions.
forbidden_phrase := "restart all"

deny_forbidden_text {
  lower(input.step.action) != ""
  contains(lower(input.step.action), forbidden_phrase)
}

allow {
  not deny_forbidden_text
  at := lower(input.step.action_type)
  at != ""
  allowed_action_types[at]
}

