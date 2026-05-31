terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.45"
    }
  }

  # Remote state (recommended for stage/prod). Create bucket + enable versioning first.
  # See README.md — uncomment after `gcloud storage buckets create gs://YOUR-TF-STATE-BUCKET`.
  #
  # backend "gcs" {
  #   bucket = "spaceops-terraform-state"
  #   prefix = "gcp/stage"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
  # Required for billingbudgets API when using user ADC (PS6.9 budget alerts).
  user_project_override = true
  billing_project       = var.project_id
}
