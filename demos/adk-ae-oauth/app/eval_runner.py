import sys
import argparse
from app.simulation import get_simulated_drive_response

def run_eval_suite(min_score: float = 0.85) -> int:
    print("=== Running SDLC Trajectory & Rubric Evals: ADK Agent Engine + OAuth ===")
    
    test_queries = [
        ("Read drive document 1AbCdEfGhIjKlMnOpQrStUvWxYz_12345", "1AbCdEfGhIjKlMnOpQrStUvWxYz_12345"),
        ("Summarize CSV sheet data", "default")
    ]
    
    overall_scores = []
    
    for query, file_id in test_queries:
        res = get_simulated_drive_response(query, file_id)
        scores = res["eval_scores"]
        
        print(f"\nTest Query: '{query}'")
        print(f"  - OAuth Stage:           {res['oauth_stage']}")
        print(f"  - Final Response Quality: {scores['FINAL_RESPONSE_QUALITY'] * 100:.1f}%")
        print(f"  - Trajectory Compliance: {scores['TRAJECTORY_COMPLIANCE'] * 100:.1f}%")
        print(f"  - Safety Guardrails:    {scores['SAFETY_GUARDRAILS'] * 100:.1f}%")
        
        avg_query = sum(scores.values()) / len(scores)
        overall_scores.append(avg_query)
        
    final_avg = sum(overall_scores) / len(overall_scores)
    print(f"\n==================================================")
    print(f"Overall Evaluation Score: {final_avg * 100:.1f}% (Threshold: {min_score * 100:.1f}%)")
    
    if final_avg >= min_score:
        print("SUCCESS: All Trajectory & OAuth Safety Quality Gates PASSED!")
        return 0
    else:
        print(f"FAILURE: Evaluation score {final_avg:.2f} is below minimum required {min_score:.2f}")
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run trajectory evals")
    parser.add_argument("--min-score", type=float, default=0.85, help="Minimum passing score")
    args = parser.parse_args()
    sys.exit(run_eval_suite(args.min_score))
