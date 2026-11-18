"""Shared Google Gen AI client helper for Gemini 4 Hydrogen."""

import os
from google import genai

MODEL_ID = os.environ.get("GEMINI_MODEL", "gemini-4-hydrogen")


def get_client() -> genai.Client:
    """Return a configured genai.Client.

    Uses GEMINI_API_KEY / GOOGLE_API_KEY if set; otherwise uses Vertex AI
    with GCP_PROJECT and GCP_LOCATION (default: global).
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)

    project = os.environ.get("GCP_PROJECT", "")
    if not project:
        raise RuntimeError("Set GCP_PROJECT (or GEMINI_API_KEY) before running live Gemini 4 Hydrogen calls.")
    location = os.environ.get("GCP_LOCATION", "global")
    return genai.Client(vertexai=True, project=project, location=location)
