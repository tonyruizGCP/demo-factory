#!/usr/bin/env python3
"""ACME Retail Store KPI Calculator Script."""

import argparse
import json
import sys

def calculate_kpis(revenue: float, target: float, traffic: int, transactions: int, labor_hours: float) -> dict:
    variance_dollars = revenue - target
    variance_pct = (variance_dollars / target * 100.0) if target > 0 else 0.0
    conversion_rate = (transactions / traffic * 100.0) if traffic > 0 else 0.0
    aov = (revenue / transactions) if transactions > 0 else 0.0
    splh = (revenue / labor_hours) if labor_hours > 0 else 0.0

    # Benchmark classifications
    status_variance = "🟢 Outperforming" if variance_pct >= 5.0 else ("🟢 On Target" if variance_pct >= 0.0 else ("🟡 Needs Attention" if variance_pct >= -5.0 else "🔴 Critical Shortfall"))
    status_conversion = "🟢 Healthy" if conversion_rate >= 24.5 else ("🟡 Sub-optimal" if conversion_rate >= 20.0 else "🔴 Low Conversion")
    status_splh = "🟢 Highly Efficient" if splh >= 220.0 else ("🟢 On Target" if splh >= 185.0 else ("🟡 Inefficient" if splh >= 160.0 else "🔴 Severe Labor Drag"))

    return {
        "revenue_actual": round(revenue, 2),
        "revenue_target": round(target, 2),
        "variance_dollars": round(variance_dollars, 2),
        "variance_percent": round(variance_pct, 2),
        "conversion_rate_percent": round(conversion_rate, 2),
        "average_order_value": round(aov, 2),
        "sales_per_labor_hour": round(splh, 2),
        "evaluation_flags": {
            "budget_status": status_variance,
            "conversion_status": status_conversion,
            "labor_status": status_splh
        }
    }

def main():
    parser = argparse.ArgumentParser(description="Calculate store performance metrics.")
    parser.add_argument("--revenue", type=float, required=True, help="Actual gross revenue ($)")
    parser.add_argument("--target", type=float, required=True, help="Budgeted revenue target ($)")
    parser.add_argument("--traffic", type=int, required=True, help="Foot traffic (visitor count)")
    parser.add_argument("--transactions", type=int, required=True, help="Total transaction count")
    parser.add_argument("--labor_hours", type=float, required=True, help="Total scheduled labor hours")
    
    args = parser.parse_args()
    results = calculate_kpis(args.revenue, args.target, args.traffic, args.transactions, args.labor_hours)
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
