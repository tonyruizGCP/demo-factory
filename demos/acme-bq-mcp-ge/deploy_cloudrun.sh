#!/usr/bin/env bash
set -e

# Load environment variables
if [ -f .env ]; then
  source .env
fi

SERVICE_NAME="acme-async-bq-mcp"
GCP_PROJECT_ID="${GCP_PROJECT_ID:-truiz-agy-demo}"
GCP_REGION="${GCP_REGION:-us-central1}"
BQ_DATASET_ID="${BQ_DATASET_ID:-acme_media_intelligence}"
BQ_LOCATION="${BQ_LOCATION:-US}"

echo "🔑 Fetching fresh Application Default Credentials (ADC) token..."
ADC_TOKEN=$(python3 -c "
import google.auth, google.auth.transport.requests
creds, _ = google.auth.default()
req = google.auth.transport.requests.Request()
creds.refresh(req)
print(creds.token)
")

export CLOUDSDK_AUTH_ACCESS_TOKEN="$ADC_TOKEN"

echo "🚀 Deploying ${SERVICE_NAME} to Cloud Run in project ${GCP_PROJECT_ID} (${GCP_REGION})..."

gcloud run deploy "${SERVICE_NAME}" \
  --project="${GCP_PROJECT_ID}" \
  --region="${GCP_REGION}" \
  --source="." \
  --allow-unauthenticated \
  --set-env-vars="GCP_PROJECT_ID=${GCP_PROJECT_ID},BQ_DATASET_ID=${BQ_DATASET_ID},BQ_LOCATION=${BQ_LOCATION}" \
  --quiet

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --project="${GCP_PROJECT_ID}" --region="${GCP_REGION}" --format="value(status.url)")

echo "================================================================="
echo "✅ Cloud Run MCP Deployment Successful!"
echo "👉 MCP Server URL for Gemini Enterprise: ${SERVICE_URL}/mcp"
echo "================================================================="
