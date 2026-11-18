# OpenMARCIE (`Vol10`) × Gemini 4 Hydrogen

A **Demo Factory** multimodal showcase using a selective `618 KB` cropped 90-second clip (+ 3 keyframes) from the 197 GB [OpenMarcieA_Main](https://www.kaggle.com/datasets/4942046dbb2608f5a0c3e76c9bd53c6b9b2784d738da7db37f7739b89c2c7f95?select=Vol10) dataset, powered by **`gemini-4-hydrogen`** (`locations/global`).

## Quick Start

```bash
# 1. Run automated tests & offline trajectory evals
make test
make eval

# 2. Launch the web UI (uses live Vertex AI if authenticated, or simulated fallback)
export GCP_PROJECT=<your-gcp-project-id>
make run
```

## Capabilities Showcased
1. **Temporal Action Recognition (Video → JSON):** Chronological segmentation with `AssemblyTimeline` / `ActionSegment` Pydantic schemas.
2. **Spatial & State-Transition Reasoning (3 Keyframes → Markdown):** Multi-image comparison across `t=00s`, `t=30s`, and `t=60s`.
3. **Industrial SOP & EHS Audit (Video → Report):** Ergonomics, PPE/hazard checks, and cycle-time recommendations with `gemini-4-hydrogen` thinking traces.

## Research Context
See [RESEARCH_WRITEUP.md](RESEARCH_WRITEUP.md) for a detailed comparison of how **`gemini-4-hydrogen`** pushes beyond the CVPR '26 OpenMarcie paper's supervised baselines (ViT/DeepConvLSTM HAR, `Vec2Text` captioning, and `InfoNCE` alignment).
