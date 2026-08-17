output "cloud_run_service_url" {
  description = "The public HTTPS endpoint URL of the deployed SOC Operations Dashboard."
  value       = google_cloud_run_v2_service.eval_dashboard.uri
}

output "artifact_registry_repo" {
  description = "Artifact Registry repository URI for container builds."
  value       = google_artifact_registry_repository.eval_repo.id
}

output "trajectory_storage_bucket" {
  description = "Google Cloud Storage bucket name for persistent evaluation runs."
  value       = google_storage_bucket.trajectory_store.name
}
