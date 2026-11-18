"""High-fidelity offline simulation responses for Demo Factory resilience."""

from typing import Any


def get_simulated_response(mode: str, thinking_level: str = "MEDIUM") -> dict[str, Any]:
    """Return realistic simulated Gemini 4 Hydrogen responses when offline."""
    if mode == "temporal_actions":
        return {
            "mode": mode,
            "model": "gemini-4-hydrogen (simulated)",
            "thinking_level": thinking_level,
            "thoughts": (
                "1. Inspecting the 90s OpenMARCIE Vol10 exocentric window view (360x266 cropped).\n"
                "2. Tracking worker posture and hand-bike interactions near the central repair stand.\n"
                "3. Segmenting into coherent assembly intervals with MM:SS boundaries."
            ),
            "result": {
                "scene_summary": (
                    "Single worker assembling and adjusting a red/silver bicycle mounted on a floor "
                    "stand in an instrumented workshop with a green workbench and parts shelving."
                ),
                "total_segments": 4,
                "segments": [
                    {
                        "start_time": "00:00",
                        "end_time": "00:22",
                        "action_label": "Inspect and align front fork / handlebar",
                        "components_or_tools": ["bicycle frame", "handlebar", "front wheel"],
                        "worker_posture": "crouching",
                        "visual_evidence": "Worker crouches beside the front wheel, adjusting alignment.",
                    },
                    {
                        "start_time": "00:22",
                        "end_time": "00:46",
                        "action_label": "Adjust brake/cable routing near stem",
                        "components_or_tools": ["stem", "brake cable", "hand tool"],
                        "worker_posture": "standing bent forward",
                        "visual_evidence": "Worker stands upright, leaning over the handlebar assembly.",
                    },
                    {
                        "start_time": "00:46",
                        "end_time": "01:08",
                        "action_label": "Retrieve part from workbench",
                        "components_or_tools": ["workbench", "small fastener"],
                        "worker_posture": "walking / standing",
                        "visual_evidence": "Worker steps toward the green table on the right and returns.",
                    },
                    {
                        "start_time": "01:08",
                        "end_time": "01:30",
                        "action_label": "Tighten component on bicycle frame",
                        "components_or_tools": ["wrench/hex key", "bicycle frame"],
                        "worker_posture": "bending",
                        "visual_evidence": "Worker resumes working on the central frame assembly.",
                    },
                ],
            },
        }

    if mode == "spatial_transitions":
        return {
            "mode": mode,
            "model": "gemini-4-hydrogen (simulated)",
            "thinking_level": thinking_level,
            "thoughts": (
                "Comparing 3 keyframes (t=00s, t=30s, t=60s) from OpenMARCIE Vol10. "
                "Checking worker stance, bicycle orientation on stand, and workbench state."
            ),
            "result": (
                "### Multi-Frame Spatial & State-Transition Analysis\n\n"
                "1. **Worker Position & Posture**:\n"
                "   - **t=00s**: Worker is positioned low/crouched on the left side of the bicycle.\n"
                "   - **t=30s**: Worker is standing upright, leaning slightly toward the handlebar/stem.\n"
                "   - **t=60s**: Worker shifts stance around the front assembly to access fasteners.\n\n"
                "2. **Assembly Progress**:\n"
                "   - The bicycle remains stabilized in the floor stand while upper-frame/cockpit "
                "components are fitted and aligned.\n\n"
                "3. **Workbench & Workspace State**:\n"
                "   - The laptop and instruction sheet remain stationary on the green workbench; "
                "the floor mat around the stand remains clear."
            ),
        }

    return {
        "mode": "ehs_audit",
        "model": "gemini-4-hydrogen (simulated)",
        "thinking_level": thinking_level,
        "thoughts": (
            "Evaluating ergonomics, PPE visibility, floor hazards, and motion waste across "
            "the 90-second OpenMARCIE Vol10 clip."
        ),
        "result": (
            "### Industrial SOP & EHS Audit Report (OpenMARCIE Vol10)\n\n"
            "1. **Ergonomics & Posture**:\n"
            "   - **00:00–00:22 & 01:08–01:30**: Prolonged crouching and forward spinal flexion "
            "while working at wheel/hub height. Raising the bicycle onto an elevated repair stand "
            "would reduce lower-back strain.\n\n"
            "2. **PPE & Safety Observations**:\n"
            "   - Closed-toe footwear is visible; safety eyewear and cut/grip gloves are not "
            "clearly discernible from the exocentric angle.\n"
            "   - **Floor Hazard**: Minor loose items/cables near the right edge of the dark mat "
            "should be kept clear of the walk path to the workbench.\n\n"
            "3. **Process Efficiency**:\n"
            "   - **Recommendations**: (a) Use an adjustable-height bike workstand; (b) stage "
            "frequently used hex keys and fasteners on a rolling tool tray beside the stand to "
            "eliminate trips to the green workbench."
        ),
    }
