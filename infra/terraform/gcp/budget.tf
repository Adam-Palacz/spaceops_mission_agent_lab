# PS6.9 — optional billing budget + email alerts (stretch: enable on live project).

data "google_project" "current" {
  count = var.enable_budget_alert ? 1 : 0

  project_id = var.project_id

  depends_on = [google_project_service.apis]
}

locals {
  billing_account_id = replace(var.billing_account_id, "billingAccounts/", "")
}

resource "google_project_service" "budget_apis" {
  for_each = var.enable_budget_alert ? toset([
    "billingbudgets.googleapis.com",
    "monitoring.googleapis.com",
  ]) : toset([])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_monitoring_notification_channel" "budget_email" {
  for_each = var.enable_budget_alert ? toset(var.budget_alert_emails) : toset([])

  project      = var.project_id
  display_name = "spaceops-budget-${var.environment}-${replace(each.value, "@", "-at-")}"
  type         = "email"

  labels = {
    email_address = each.value
  }

  depends_on = [google_project_service.budget_apis]
}

resource "google_billing_budget" "spaceops" {
  count = var.enable_budget_alert ? 1 : 0

  billing_account = local.billing_account_id
  display_name    = "spaceops-${var.environment}-monthly"

  budget_filter {
    # Billing API expects project *number*, not project ID.
    projects = ["projects/${data.google_project.current[0].number}"]
  }

  amount {
    specified_amount {
      currency_code = var.budget_currency_code
      units         = tostring(var.budget_amount_usd)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 0.9
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "FORECASTED_SPEND"
  }

  all_updates_rule {
    monitoring_notification_channels = [
      for email in var.budget_alert_emails :
      google_monitoring_notification_channel.budget_email[email].name
    ]
    disable_default_iam_recipients   = false
    enable_project_level_recipients  = true
  }

  depends_on = [google_project_service.budget_apis]
}
