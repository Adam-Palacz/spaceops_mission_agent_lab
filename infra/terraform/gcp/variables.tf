variable "project_id" {
  description = "GCP project ID (billing must be enabled)."
  type        = string
}

variable "region" {
  description = "Primary region for GKE, Artifact Registry, and regional resources."
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment label for cost allocation (dev | stage | prod)."
  type        = string
  default     = "stage"

  validation {
    condition     = contains(["dev", "stage", "prod"], var.environment)
    error_message = "environment must be dev, stage, or prod."
  }
}

variable "cluster_name" {
  description = "GKE cluster name."
  type        = string
  default     = "spaceops-stage"
}

variable "node_locations" {
  description = "GKE node zones for the regional lab cluster. Keep single-zone by default to reduce quota/cost."
  type        = list(string)
  default     = ["us-central1-a"]
}

variable "deletion_protection" {
  description = "GKE deletion protection. Set false for ephemeral lab clusters (terraform destroy)."
  type        = bool
  default     = false
}

variable "node_count" {
  description = "Initial node count in the default node pool (keep small for lab/stage)."
  type        = number
  default     = 1
}

variable "machine_type" {
  description = "GCE machine type for the default node pool."
  type        = string
  default     = "e2-standard-2"
}

variable "preemptible_nodes" {
  description = "Use preemptible VMs in the node pool to reduce stage cost."
  type        = bool
  default     = true
}

variable "node_disk_size_gb" {
  description = "Boot disk size per node (keep small on fresh projects — SSD quota)."
  type        = number
  default     = 30
}

variable "node_disk_type" {
  description = "Boot disk type (pd-standard avoids SSD_TOTAL_GB quota on small projects)."
  type        = string
  default     = "pd-standard"
}

variable "enable_eso_workload_identity_binding" {
  description = "Bind ESO K8s SA to GSA via Workload Identity (requires GKE cluster first)."
  type        = bool
  default     = true
}

variable "artifact_registry_repository_id" {
  description = "Artifact Registry Docker repository ID."
  type        = string
  default     = "spaceops"
}

variable "deploy_service_account_id" {
  description = "Service account ID (without domain) for CI/Helm deploy."
  type        = string
  default     = "spaceops-deploy"
}

variable "enable_apis" {
  description = "Enable required GCP APIs via Terraform (set false if pre-enabled)."
  type        = bool
  default     = true
}

# PS6.9 — billing budget alerts (optional; requires live billing account).
variable "enable_budget_alert" {
  description = "Create monthly billing budget with email threshold alerts."
  type        = bool
  default     = false
}

variable "billing_account_id" {
  description = "Billing account ID (012345-678901-ABCDEF) or full billingAccounts/... name. Required when enable_budget_alert is true."
  type        = string
  default     = ""

  validation {
    condition = (
      var.enable_budget_alert == false
      || can(regex("^(billingAccounts/)?[A-Z0-9]{6}-[A-Z0-9]{6}-[A-Z0-9]{6}$", var.billing_account_id))
    )
    error_message = "billing_account_id must be a billing account ID like 012345-678901-ABCDEF or billingAccounts/012345-678901-ABCDEF."
  }
}

variable "budget_amount_usd" {
  description = "Monthly budget cap in budget_currency_code units for the project filter."
  type        = number
  default     = 150
}

variable "budget_currency_code" {
  description = "Billing budget currency code. Must match the billing account currency, e.g. PLN or USD."
  type        = string
  default     = "PLN"
}

variable "budget_alert_emails" {
  description = "Email addresses for budget threshold notifications."
  type        = list(string)
  default     = []

  validation {
    condition     = var.enable_budget_alert == false || length(var.budget_alert_emails) > 0
    error_message = "budget_alert_emails must be non-empty when enable_budget_alert is true."
  }
}
