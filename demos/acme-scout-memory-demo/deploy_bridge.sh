#!/usr/bin/env bash
#
# Setup and Deploy Script for GECX Long-Term Memory Bridge
# This script automates Google Cloud setup, Cloud Run deployment, and GECX integration.

set -euo pipefail

# Text formatting helpers
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================================================${NC}"
echo -e "${BLUE}     Deploying GECX Long-Term Memory Bridge to Google Cloud Run      ${NC}"
echo -e "${BLUE}=====================================================================${NC}"

# 1. Validate gcloud CLI
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed. Please install it and try again.${NC}"
    exit 1
fi

# Get active GCP Project
PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
if [[ -z "$PROJECT_ID" ]]; then
    echo -e "${RED}Error: No active Google Cloud project configured in gcloud CLI.${NC}"
    echo -e "Please run: ${YELLOW}gcloud config set project [YOUR_PROJECT_ID]${NC}"
    exit 1
fi

if [[ "$PROJECT_ID" != "truiz-cx-agent-studio" ]]; then
    echo -e "${YELLOW}Warning: Your active gcloud project is '$PROJECT_ID' instead of 'truiz-cx-agent-studio'.${NC}"
    read -r -p "Would you like to switch your active gcloud project to 'truiz-cx-agent-studio' now? (y/N): " switch_project
    if [[ "$switch_project" =~ ^[Yy]$ ]]; then
        gcloud config set project truiz-cx-agent-studio
        PROJECT_ID="truiz-cx-agent-studio"
        echo -e "${GREEN}Project successfully switched to '$PROJECT_ID'.${NC}"
    else
        echo -e "${YELLOW}Proceeding with current project '$PROJECT_ID'...${NC}"
    fi
fi


# Prompt user for Reasoning Engine / Memory Bank resource name
echo -e "\n${YELLOW}Please enter your Vertex AI Memory Bank resource name (from Step 2 of the Colab notebook):${NC}"
echo -e "Format: projects/[PROJECT_NUMBER]/locations/us-central1/reasoningEngines/[ENGINE_ID]"
read -r -p "Memory Bank ID: " INSTANCE_NAME

if [[ -z "$INSTANCE_NAME" ]]; then
    echo -e "${RED}Error: Memory Bank resource name is required.${NC}"
    exit 1
fi

LOCATION="us-central1"
SERVICE_NAME="cxas-memory-bridge"

# 2. Enable Required APIs
echo -e "\n${BLUE}[1/5] Enabling required GCP APIs...${NC}"
gcloud services enable \
    aiplatform.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    iam.googleapis.com

# 3. Build and Deploy Cloud Run Service
echo -e "\n${BLUE}[2/5] Deploying Cloud Run Service: ${SERVICE_NAME}...${NC}"
cd "$(dirname "$0")/cxas-memory-bridge"

gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region "$LOCATION" \
    --set-env-vars PROJECT_ID="$PROJECT_ID",LOCATION="$LOCATION",INSTANCE_NAME="$INSTANCE_NAME" \
    --no-allow-unauthenticated

# Extract Deployed URL
echo -e "\n${BLUE}[3/5] Constructing internal service URL...${NC}"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
RUN_URL="https://${SERVICE_NAME}-${PROJECT_NUMBER}.${LOCATION}.run.app"
echo -e "${GREEN}Deployed Service URL:${NC} ${YELLOW}$RUN_URL${NC}"

# 4. Update GECX OpenAPI Schema with Deployed URL
echo -e "\n${BLUE}[4/5] Updating OpenAPI schema with the live URL...${NC}"
SCHEMA_FILE="../cxas_app/toolsets/vertex_memory_tool/open_api_toolset/open_api_schema.yaml"

if [[ -f "$SCHEMA_FILE" ]]; then
    # Use sed to replace the server url in the OpenAPI schema
    # Use | as delimiter since URL contains slashes
    sed -i "s|url: \".*\"|url: \"$RUN_URL\"|g" "$SCHEMA_FILE"
    echo -e "${GREEN}Updated schema file:${NC} $SCHEMA_FILE"
else
    echo -e "${RED}Warning: OpenAPI Schema file not found at $SCHEMA_FILE.${NC}"
fi

# 5. Grant invoker role to the CES/GECX Service Agent
echo -e "\n${BLUE}[5/5] Granting permissions to GECX Service Agent...${NC}"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
SERVICE_AGENT="service-$PROJECT_NUMBER@gcp-sa-ces.iam.gserviceaccount.com"

echo -e "Granting ${YELLOW}roles/run.invoker${NC} to ${YELLOW}$SERVICE_AGENT${NC}..."
gcloud run services add-iam-policy-binding "$SERVICE_NAME" \
    --region "$LOCATION" \
    --member="serviceAccount:$SERVICE_AGENT" \
    --role="roles/run.invoker"

echo -e "\n${GREEN}=====================================================================${NC}"
echo -e "${GREEN}                    DEPLOYMENT COMPLETED SUCCESSFULLY                 ${NC}"
echo -e "${GREEN}=====================================================================${NC}"
echo -e "Your Cloud Run Memory Bridge is live, private, and fully authenticated."
echo -e "\nTo import this app into CX Agent Studio using SCRAPI, run:"
echo -e "  ${YELLOW}cxas push --app-dir cxas_app --to projects/truiz-cx-agent-studio/locations/us/apps/009c4736-ae05-45ed-82c6-8a31c2f7ea33${NC}"
echo -e "====================================================================="
