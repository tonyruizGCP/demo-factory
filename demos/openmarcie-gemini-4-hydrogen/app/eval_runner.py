"""Offline evaluation & schema verification runner for Demo Factory CI."""

import os

os.environ["DEMO_SIMULATION"] = "1"

from app.agent import AssemblyTimeline, run_multimodal_analysis


def main() -> None:
    modes = ["temporal_actions", "spatial_transitions", "ehs_audit"]
    for mode in modes:
        res = run_multimodal_analysis(mode=mode, thinking_level="MEDIUM")
        assert res["mode"] == mode, f"Mode mismatch: {res}"
        if mode == "temporal_actions":
            parsed = AssemblyTimeline.model_validate(res["result"])
            assert parsed.total_segments >= 1
        else:
            assert isinstance(res["result"], str) and len(res["result"]) > 40
    print("EVAL_OK: All 3 Gemini 4 Hydrogen multimodal trajectories passed.")


if __name__ == "__main__":
    main()
