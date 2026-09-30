#!/usr/bin/env bash
# Deploy Acme Inc. Creative Studio MCP App to Cloud Run with Cooley Law MCP App Golden Flags
set -euo pipefail

PROJECT_ID="${GCP_PROJECT:-truiz-agy-demo}"
REGION="${GCP_LOCATION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-acme-creative-studio-mcp}"
GCS_BUCKET="${GCS_CREATIVE_BUCKET:-${PROJECT_ID}-acme-creative-studio-assets}"

echo "=================================================================="
echo " Deploying Acme Inc. Creative Studio MCP App to Cloud Run"
echo " Project:      ${PROJECT_ID}"
echo " Region:       ${REGION}"
echo " Service:      ${SERVICE_NAME}"
echo " GCS Bucket:   gs://${GCS_BUCKET}"
echo "=================================================================="

# Ensure GCS bucket exists if deploying live
if ! gcloud storage buckets describe "gs://${GCS_BUCKET}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Creating GCS bucket gs://${GCS_BUCKET}..."
  gcloud storage buckets create "gs://${GCS_BUCKET}" --project="${PROJECT_ID}" --location="${REGION}" --uniform-bucket-level-access --public-access-prevention
fi

PROJECT_NUM="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
RUNTIME_SA="${PROJECT_NUM}-compute@developer.gserviceaccount.com"
echo "Granting storage.objectAdmin on gs://${GCS_BUCKET} and aiplatform.user to ${RUNTIME_SA}..."
gcloud storage buckets add-iam-policy-binding "gs://${GCS_BUCKET}" \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/storage.objectAdmin" \
  --project="${PROJECT_ID}" >/dev/null 2>&1 || true

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/aiplatform.user" \
  --condition=None \
  --quiet >/dev/null 2>&1 || true


# Deploy with Golden Cloud Run Flags for Gemini Enterprise MCP Apps:
# --no-cpu-throttling : Keeps background asyncio Gemini Omni + Nano Banana jobs running between polls
# --min-instances 1 --max-instances 1 : Single warm stateful instance + zero cold-start timeout
# --concurrency 80 : Prevents Envoy 503 'overloaded' during concurrent AppBridge polls
gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --allow-unauthenticated \
  --no-cpu-throttling \
  --min-instances 1 \
  --max-instances 1 \
  --concurrency 80 \
  --memory 2Gi \
  --cpu 2 \
  --set-env-vars "GCP_PROJECT=${PROJECT_ID},GCP_LOCATION=global,GCS_CREATIVE_BUCKET=${GCS_BUCKET},GEMINI_OMNI_MODEL=gemini-omni-flash-preview,NANO_BANANA_MODEL=gemini-3.1-flash-image-preview"

SERVICE_URL="$(gcloud run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format='value(status.url)')"
PROJECT_NUM="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"

echo "Granting Discovery Engine P4SA & allUsers Cloud Run Invoker..."
gcloud run services add-iam-policy-binding "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --member="allUsers" \
  --role="roles/run.invoker" >/dev/null

gcloud run services add-iam-policy-binding "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --member="serviceAccount:service-${PROJECT_NUM}@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
  --role="roles/run.invoker" >/dev/null || true

echo ""
echo "✅ Deployed Acme Creative Studio MCP Server!"
echo "   Cloud Run URL:  ${SERVICE_URL}"
echo "   MCP Endpoint:   ${SERVICE_URL}/mcp"
echo "   Standalone UI:  ${SERVICE_URL}/app"
