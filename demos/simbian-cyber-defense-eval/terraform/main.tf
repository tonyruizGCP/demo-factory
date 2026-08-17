provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# 1. Enable Required Google Cloud APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "aiplatform.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "storage.googleapis.com",
    "cloudbuild.googleapis.com",
  ])
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

# 2. Artifact Registry for Container Sandboxes
resource "google_artifact_registry_repository" "eval_repo" {
  depends_on    = [google_project_service.required_apis]
  location      = var.region
  repository_id = "cyber-evals"
  description   = "Docker repository for Harbor sandbox container images and SOC Web Dashboard"
  format        = "DOCKER"
}

# 3. Google Cloud Storage Bucket for Evaluation Trajectories & Golden Slices
resource "google_storage_bucket" "trajectory_store" {
  depends_on                  = [google_project_service.required_apis]
  name                        = "${var.project_id}-cyber-eval-trajectories"
  location                    = var.region
  uniform_bucket_level_access = true
  versioning {
    enabled = true
  }
}

# 4. Service Account for Agent Evaluation Runner
resource "google_service_account" "eval_runner_sa" {
  account_id   = "cyber-eval-runner"
  display_name = "Cyber Defense Evaluation Runner Service Account"
}

# 5. Grant Vertex AI User & Storage Object Admin to Service Account
resource "google_project_iam_member" "vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.eval_runner_sa.email}"
}

resource "google_storage_bucket_iam_member" "storage_admin" {
  bucket = google_storage_bucket.trajectory_store.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.eval_runner_sa.email}"
}

# 6. Cloud Run Service for SOC Operations Dashboard
resource "google_cloud_run_v2_service" "eval_dashboard" {
  depends_on = [google_project_service.required_apis]
  name       = var.service_name
  location   = var.region
  ingress    = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.eval_runner_sa.email

    containers {
      image = var.container_image

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }

      ports {
        container_port = 8080
      }
    }
  }
}

# 7. IAM Policy for Cloud Run (Public or Organization Access)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.eval_dashboard.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
