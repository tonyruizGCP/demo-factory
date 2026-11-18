# OpenMARCIE Vol10 × Gemini 4 Hydrogen — Demo Factory Guidelines

- **Model**: `gemini-4-hydrogen` via Vertex AI `location="global"` (`google-genai` SDK).
- **Entrypoint**: `app/agent.py` exports `root_agent` and `app`.
- **Environment Variables**: Uses `GCP_PROJECT` (never `GOOGLE_CLOUD_PROJECT` in `app/`) and dynamic `PORT` binding.
- **Payload Isolation**: Raw 152 MB Kaggle video stays in `data/` (`.gitignore`d); only the `618 KB` cropped clip and 3 keyframes (`~32 KB`) live in `static/media/`.
- **Offline Resilience**: All `/api/analyze` modes fall back to `app/simulation.py` when `DEMO_SIMULATION=1` or GCP credentials are unavailable.
