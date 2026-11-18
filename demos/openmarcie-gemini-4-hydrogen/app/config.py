"""Configuration for OpenMARCIE Vol10 × Gemini 4 Hydrogen Demo."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
MEDIA_DIR = STATIC_DIR / "media"

CLIP_PATH = MEDIA_DIR / "vol10_window_90s_cropped.mp4"
KEYFRAMES = [
    ("t=00s", MEDIA_DIR / "cropped_00s.jpg"),
    ("t=30s", MEDIA_DIR / "cropped_30s.jpg"),
    ("t=60s", MEDIA_DIR / "cropped_60s.jpg"),
]

# Demo Factory guardrail: use GCP_PROJECT env var in app/
GCP_PROJECT = os.environ.get("GCP_PROJECT", "")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "global")
MODEL_ID = os.environ.get("GEMINI_MODEL", "gemini-4-hydrogen")
FORCE_SIMULATION = os.environ.get("DEMO_SIMULATION", "0") == "1"
