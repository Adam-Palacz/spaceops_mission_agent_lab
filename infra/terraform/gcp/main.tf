locals {
  common_labels = {
    app         = "spaceops"
    env         = var.environment
    managed_by  = "terraform"
    sprint      = "ps68"
  }

  required_apis = [
    "container.googleapis.com",
    "artifactregistry.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
  ]
}

resource "google_project_service" "apis" {
  for_each = var.enable_apis ? toset(local.required_apis) : toset([])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "spaceops" {
  location      = var.region
  repository_id = var.artifact_registry_repository_id
  description   = "SpaceOps container images (api, mcp, …)"
  format        = "DOCKER"
  labels        = local.common_labels

  depends_on = [google_project_service.apis]
}

resource "google_service_account" "deploy" {
  account_id   = var.deploy_service_account_id
  display_name = "SpaceOps deploy / CI (${var.environment})"
  description  = "Push images to Artifact Registry and deploy Helm to GKE."
}

resource "google_project_iam_member" "deploy_artifact_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.deploy.email}"
}

resource "google_project_iam_member" "deploy_gke_developer" {
  project = var.project_id
  role    = "roles/container.developer"
  member  = "serviceAccount:${google_service_account.deploy.email}"
}

# External Secrets Operator → Google Secret Manager (PS6.6 design note).
resource "google_service_account" "eso" {
  account_id   = "spaceops-eso-${var.environment}"
  display_name = "SpaceOps ESO (${var.environment})"
  description  = "Workload Identity SA for External Secrets Operator GSM access."
}

resource "google_project_iam_member" "eso_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.eso.email}"
}

resource "google_service_account_iam_member" "eso_wi_user" {
  service_account_id = google_service_account.eso.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[external-secrets/external-secrets]"
}

resource "google_container_cluster" "primary" {
  name     = var.cluster_name
  location = var.region

  # Small lab/stage cluster — single default node pool; no GPU (Phase 7).
  remove_default_node_pool = true
  initial_node_count       = 1

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  release_channel {
    channel = "REGULAR"
  }

  resource_labels = local.common_labels

  depends_on = [google_project_service.apis]
}

resource "google_container_node_pool" "primary" {
  name       = "${var.cluster_name}-pool"
  location   = var.region
  cluster    = google_container_cluster.primary.name
  node_count = var.node_count

  node_config {
    machine_type = var.machine_type
    preemptible  = var.preemptible_nodes

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]

    labels = local.common_labels

    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# Allow GKE nodes to pull images from Artifact Registry in the same project.
data "google_compute_default_service_account" "default" {
  project = var.project_id
}

resource "google_project_iam_member" "gke_nodes_ar_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${data.google_compute_default_service_account.default.email}"
}
