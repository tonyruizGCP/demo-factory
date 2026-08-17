variable "project_id" {
  type        = string
  description = "The Google Cloud Project ID to provision the cyber defense evaluation infrastructure within."
  default     = "truiz-agent-builder"
}

variable "region" {
  type        = string
  description = "The GCP region for Cloud Run and Vertex AI Agent Engine resources."
  default     = "us-central1"
}

variable "service_name" {
  type        = string
  description = "Name of the Cloud Run SOC Operations Dashboard service."
  default     = "simbian-cyber-defense-eval"
}

variable "container_image" {
  type        = string
  description = "Container image URI in Google Artifact Registry."
  default     = "us-central1-docker.pkg.dev/truiz-agent-builder/cyber-evals/dashboard:latest"
}
