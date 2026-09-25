#!/usr/bin/env bash
set -e

PORT="${PORT:-8080}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --use-managed-services)
      export USE_MANAGED_SERVICES="true"
      shift
      ;;
    --no-managed-services)
      export USE_MANAGED_SERVICES="false"
      shift
      ;;
    --use-managed-sessions)
      export USE_MANAGED_SESSIONS="true"
      shift
      ;;
    --no-managed-sessions)
      export USE_MANAGED_SESSIONS="false"
      shift
      ;;
    --use-managed-memory-bank)
      export USE_MANAGED_MEMORY_BANK="true"
      shift
      ;;
    --no-managed-memory-bank)
      export USE_MANAGED_MEMORY_BANK="false"
      shift
      ;;
    --port=*)
      PORT="${1#*=}"
      shift
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --project-id=*)
      export GCP_PROJECT="${1#*=}"
      shift
      ;;
    --project-id)
      export GCP_PROJECT="$2"
      shift 2
      ;;
    --location=*)
      export GOOGLE_CLOUD_LOCATION="${1#*=}"
      shift
      ;;
    --location)
      export GOOGLE_CLOUD_LOCATION="$2"
      shift 2
      ;;
    --agent-engine-id=*)
      export GOOGLE_CLOUD_AGENT_ENGINE_ID="${1#*=}"
      shift
      ;;
    --agent-engine-id)
      export GOOGLE_CLOUD_AGENT_ENGINE_ID="$2"
      shift 2
      ;;
    *)
      # Preserve unrecognized flags for python/uvicorn if needed
      shift
      ;;
  esac
done

echo "=========================================================="
echo " Starting Gemini Enterprise Coding Harness Demo Server"
echo " Port:               $PORT"
echo " URL:                http://tonyruiz.c.googlers.com:$PORT"
echo " Managed Services:   ${USE_MANAGED_SERVICES:-false}"
echo " Managed Sessions:   ${USE_MANAGED_SESSIONS:-${USE_MANAGED_SERVICES:-false}}"
echo " Managed MemoryBank: ${USE_MANAGED_MEMORY_BANK:-${USE_MANAGED_SERVICES:-false}}"
echo " Project ID:         ${GCP_PROJECT:-${GOOGLE_CLOUD_PROJECT:-truiz-agy-demo}}"
echo " Location:           ${GOOGLE_CLOUD_LOCATION:-us-central1}"
echo " Agent Engine ID:    ${GOOGLE_CLOUD_AGENT_ENGINE_ID:-coding-harness-engine}"
echo "=========================================================="

if [[ "${DRY_RUN:-0}" != "1" ]]; then
  python3 -m uvicorn app.server:app --host 0.0.0.0 --port "$PORT" --reload
fi
