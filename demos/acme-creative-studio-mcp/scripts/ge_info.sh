#!/usr/bin/env bash
# Print Gemini Enterprise Custom MCP Connector & Agent Registration Cheatsheet
set -euo pipefail

PROJECT_ID="${GCP_PROJECT:-truiz-agy-demo}"
REGION="${GCP_LOCATION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-acme-creative-studio-mcp}"
SERVICE_URL="${SERVICE_URL:-https://acme-creative-studio-mcp-442606385483.us-central1.run.app}"
GE_APP_ID="${GE_APP_ID:-acme-creative-studio-ge-app}"
CONNECTOR_ID="${CONNECTOR_ID:-acme-creative-studio-mcp}"

cat <<EOF
========================================================================
 ACME INC. CREATIVE STUDIO — GEMINI ENTERPRISE MCP APP REGISTRATION
========================================================================
Project:              ${PROJECT_ID} (442606385483)
Cloud Run Service:    ${SERVICE_URL}
MCP Endpoint URL:     ${SERVICE_URL}/mcp
Standalone Web UI:    ${SERVICE_URL}/app
GCS Version Bucket:   gs://${PROJECT_ID}-acme-creative-studio-assets
GE App (Engine) ID:   ${GE_APP_ID}
GE Data Connector:    ${CONNECTOR_ID} (acme-creative-studio-mcp_mcp_data)

1. Org Policy Prerequisite:
   Ensure 'constraints/discoveryengine.managed.disableCustomMcpServerConnector'
   is NOT enforced on project '${PROJECT_ID}'.

2. OAuth 2.0 Web Client (APIs & Services -> Credentials):
   - Authorized Redirect URIs:
     * https://vertexaisearch.cloud.google.com/console/oauth/default_oauth.html
     * https://vertexaisearch.cloud.google.com/oauth-redirect

3. Gemini Enterprise Custom MCP Server Connector:
   - Connector Name:      Acme Creative Studio Connector (${CONNECTOR_ID})
   - MCP Endpoint URL:    ${SERVICE_URL}/mcp
   - Enable PKCE:         CHECKED (Enabled)
   - HTTP Basic Auth:     UNCHECKED (Do NOT check — causes invalid_client)
   - Scopes:              openid email profile

4. Gemini Enterprise App (${GE_APP_ID}):
   - Display Name:        Acme Inc. Creative Studio (MCP App Demo)
   - Linked Data Store:   acme-creative-studio-mcp_mcp_data
   - Console URL:         https://console.cloud.google.com/gen-app-builder/engines?project=${PROJECT_ID}
========================================================================
EOF
