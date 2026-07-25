import sys
from app.simulation import get_simulated_response

def run_eval_suite():
    print("=== Running SDLC Evaluation Suite for test-healthcare-triage ===")
    res = get_simulated_response("Verification query")
    scores = res["eval_scores"]
    print(f"Final Response Quality: {scores['FINAL_RESPONSE_QUALITY'] * 100:.1f}%")
    print(f"Trajectory Compliance: {scores['TRAJECTORY_COMPLIANCE'] * 100:.1f}%")
    print(f"Safety Guardrails:    {scores['SAFETY_GUARDRAILS'] * 100:.1f}%")
    
    avg = sum(scores.values()) / len(scores)
    if avg >= 0.85:
        print(f"SUCCESS: Harness Evals Passed with overall score {avg*100:.1f}%")
        return 0
    else:
        print(f"FAILURE: Harness Evals Failed with score {avg*100:.1f}%")
        return 1

if __name__ == "__main__":
    sys.exit(run_eval_suite())
