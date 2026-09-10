#!/usr/bin/env python3
"""ACME Retail Morning Huddle Brief Compiler."""

import argparse
import json
import sys

def compile_brief(sales: float, target: float, transactions: int) -> dict:
    variance = sales - target
    variance_pct = (variance / target * 100.0) if target > 0 else 0.0
    aov = (sales / transactions) if transactions > 0 else 0.0
    
    pacing_tone = "Ahead of Target! Great momentum to maintain today." if variance >= 0 else "Slight gap to make up on today's shift."

    return {
        "sales": round(sales, 2),
        "target": round(target, 2),
        "variance_dollars": round(variance, 2),
        "variance_pct": round(variance_pct, 1),
        "transactions": transactions,
        "aov": round(aov, 2),
        "pacing_tone": pacing_tone
    }

def main():
    parser = argparse.ArgumentParser(description="Compile huddle brief metrics.")
    parser.add_argument("--sales", type=float, required=True, help="Yesterday gross sales ($)")
    parser.add_argument("--target", type=float, required=True, help="Yesterday target sales ($)")
    parser.add_argument("--transactions", type=int, required=True, help="Yesterday total transactions")
    
    args = parser.parse_args()
    result = compile_brief(args.sales, args.target, args.transactions)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
