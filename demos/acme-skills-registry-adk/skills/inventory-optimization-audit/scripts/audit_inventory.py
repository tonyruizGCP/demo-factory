#!/usr/bin/env python3
"""ACME Inventory Health Audit Script."""

import argparse
import json

def audit(total_skus: int, out_of_stock: int, low_stock: int) -> dict:
    in_stock_rate = ((total_skus - out_of_stock) / total_skus * 100.0) if total_skus > 0 else 0.0
    risk_level = "CRITICAL" if in_stock_rate < 92.0 else ("WARNING" if in_stock_rate < 96.0 else "OPTIMAL")
    
    return {
        "total_tracked_skus": total_skus,
        "out_of_stock_count": out_of_stock,
        "low_stock_warning_count": low_stock,
        "in_stock_rate_pct": round(in_stock_rate, 1),
        "inventory_health_rating": risk_level,
        "action_required": "Initiate automated replenishment PO for low-stock SKUs." if low_stock > 0 or out_of_stock > 0 else "Inventory levels within optimal threshold."
    }

def main():
    parser = argparse.ArgumentParser(description="Audit inventory health.")
    parser.add_argument("--total-skus", type=int, default=120)
    parser.add_argument("--out-of-stock", type=int, default=4)
    parser.add_argument("--low-stock", type=int, default=9)
    
    args = parser.parse_args()
    result = audit(args.total_skus, args.out_of_stock, args.low_stock)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
