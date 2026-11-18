"""Shared Google Gen AI client helper (Vertex AI or Gemini Developer API)."""

import os
from google import genai


def get_client() -> genai.Client:
    """Return a configured genai.Client.

    Uses GEMINI_API_KEY if set; otherwise defaults to Vertex AI using
    Application Default Credentials (project tonyruiz-sobi-demo, us-central1).
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)

    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "tonyruiz-sobi-demo")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    return genai.Client(vertexai=True, project=project, location=location)
