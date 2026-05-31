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
