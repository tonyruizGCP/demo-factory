#!/usr/bin/env python3
"""
Acme Gemini Enterprise App Connector Checker
Verifies discovery engine data store and app provisioning status for Acme Corp.
"""

import os
from dotenv import load_dotenv
from google.cloud import discoveryengine_v1 as discoveryengine
from google.api_core.client_options import ClientOptions

load_dotenv()

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "truiz-agy-demo")
GE_LOCATION = os.getenv("GE_LOCATION", "global")
GE_APP_ID = os.getenv("GE_APP_ID", "acme-media-intelligence-app")

print("=" * 80)
print(f" Acme Gemini Enterprise App Status Checker")
print(f" Project: {GCP_PROJECT_ID} | Location: {GE_LOCATION} | App: {GE_APP_ID}")
print("=" * 80)

client_options = ClientOptions(api_endpoint=f"{GE_LOCATION}-discoveryengine.googleapis.com" if GE_LOCATION != "global" else None)

try:
    engine_client = discoveryengine.EngineServiceClient(client_options=client_options)
    parent = f"projects/{GCP_PROJECT_ID}/locations/{GE_LOCATION}/collections/default_collection"
    engines = list(engine_client.list_engines(parent=parent))
    print(f"✅ Found {len(engines)} Engine(s) in {parent}:")
    for eng in engines:
        print(f" • {eng.name} ({eng.display_name})")
except Exception as e:
    print(f"ℹ️ Discovery Engine query: {e}")
