# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Retail Data Toolset for ACME Inc Data Analyst Agent.

Provides structured tools for querying store sales performance,
inventory status, and store metadata.
"""

from typing import Any, Dict, List
import json

MOCK_STORE_DATA = {
    "104": {
        "store_id": "104",
        "name": "ACME Downtown Chicago Flagship",
        "region": "Midwest",
        "format": "Flagship (32,000 sq ft)",
        "manager": "Elena Rostova",
        "yesterday": {
            "gross_revenue": 34850.00,
            "target_budget": 33000.00,
            "foot_traffic": 1820,
            "transaction_count": 482,
            "labor_hours": 154.0,
            "top_category": "Apparel & Outerwear",
            "departments": {
                "Apparel & Outerwear": {"revenue": 17800.00, "margin_pct": 51.2, "target": 16000.00},
                "Consumer Electronics": {"revenue": 8200.00, "margin_pct": 21.8, "target": 8500.00},
                "Home & Lifestyle": {"revenue": 5400.00, "margin_pct": 43.1, "target": 5000.00},
                "Footwear & Accessories": {"revenue": 3450.00, "margin_pct": 46.0, "target": 3500.00}
            }
        },
        "last_30_days": {
            "gross_revenue": 982500.00,
            "target_budget": 950000.00,
            "foot_traffic": 46200,
            "transaction_count": 11840,
            "labor_hours": 4480.0,
            "departments": {
                "Apparel & Outerwear": {"revenue": 492000.00, "margin_pct": 49.5, "target": 460000.00},
                "Consumer Electronics": {"revenue": 248000.00, "margin_pct": 22.4, "target": 255000.00},
                "Home & Lifestyle": {"revenue": 142500.00, "margin_pct": 42.0, "target": 135000.00},
                "Footwear & Accessories": {"revenue": 100000.00, "margin_pct": 45.2, "target": 100000.00}
            }
        }
    },
    "208": {
        "store_id": "208",
        "name": "ACME West Suburbs Center",
        "region": "Midwest",
        "format": "Supercenter (45,000 sq ft)",
        "manager": "David Miller",
        "yesterday": {
            "gross_revenue": 28400.00,
            "target_budget": 30500.00,
            "foot_traffic": 1410,
            "transaction_count": 322,
            "labor_hours": 162.0,
            "top_category": "Home & Lifestyle",
            "departments": {
                "Apparel & Outerwear": {"revenue": 9800.00, "margin_pct": 47.0, "target": 11500.00},
                "Consumer Electronics": {"revenue": 9200.00, "margin_pct": 21.0, "target": 9500.00},
                "Home & Lifestyle": {"revenue": 6200.00, "margin_pct": 44.2, "target": 6000.00},
                "Footwear & Accessories": {"revenue": 3200.00, "margin_pct": 43.5, "target": 3500.00}
            }
        },
        "last_30_days": {
            "gross_revenue": 815000.00,
            "target_budget": 860000.00,
            "foot_traffic": 39500,
            "transaction_count": 8920,
            "labor_hours": 4620.0,
            "departments": {
                "Apparel & Outerwear": {"revenue": 275000.00, "margin_pct": 46.8, "target": 310000.00},
                "Consumer Electronics": {"revenue": 265000.00, "margin_pct": 21.5, "target": 270000.00},
                "Home & Lifestyle": {"revenue": 182000.00, "margin_pct": 43.8, "target": 180000.00},
                "Footwear & Accessories": {"revenue": 93000.00, "margin_pct": 44.0, "target": 100000.00}
            }
        }
    },
    "315": {
        "store_id": "315",
        "name": "ACME Austin Metro Mall",
        "region": "South",
        "format": "Standard Retail (22,000 sq ft)",
        "manager": "Sophia Chen",
        "yesterday": {
            "gross_revenue": 22100.00,
            "target_budget": 21000.00,
            "foot_traffic": 980,
            "transaction_count": 268,
            "labor_hours": 98.0,
            "top_category": "Consumer Electronics",
            "departments": {
                "Apparel & Outerwear": {"revenue": 8900.00, "margin_pct": 48.9, "target": 8500.00},
                "Consumer Electronics": {"revenue": 7600.00, "margin_pct": 23.2, "target": 7000.00},
                "Home & Lifestyle": {"revenue": 3500.00, "margin_pct": 40.5, "target": 3500.00},
                "Footwear & Accessories": {"revenue": 2100.00, "margin_pct": 44.8, "target": 2000.00}
            }
        },
        "last_30_days": {
            "gross_revenue": 645000.00,
            "target_budget": 620000.00,
            "foot_traffic": 28400,
            "transaction_count": 7650,
            "labor_hours": 2850.0,
            "departments": {
                "Apparel & Outerwear": {"revenue": 265000.00, "margin_pct": 49.0, "target": 255000.00},
                "Consumer Electronics": {"revenue": 220000.00, "margin_pct": 23.0, "target": 205000.00},
                "Home & Lifestyle": {"revenue": 102000.00, "margin_pct": 41.2, "target": 100000.00},
                "Footwear & Accessories": {"revenue": 58000.00, "margin_pct": 45.0, "target": 60000.00}
            }
        }
    }
}

MOCK_INVENTORY_DATA = {
    "104": {
        "store_id": "104",
        "total_skus": 2450,
        "out_of_stock_skus": [
            {"sku": "APP-WTR-902", "name": "Summit GoreTex Weatherproof Jacket (M)", "dept": "Apparel", "lost_sales_est": "$1,450/week"},
            {"sku": "ELE-AUD-441", "name": "ACME Pulse ANC Wireless Earbuds (Black)", "dept": "Electronics", "lost_sales_est": "$2,200/week"}
        ],
        "low_stock_skus": [
            {"sku": "HOM-EXP-118", "name": "Barista Touch Espresso Machine", "dept": "Home", "units_left": 2, "reorder_point": 5},
            {"sku": "FTW-RUN-552", "name": "Velocity Pro Carbon Running Shoe (Size 10)", "dept": "Footwear", "units_left": 1, "reorder_point": 4}
        ],
        "in_stock_rate_pct": 98.4,
        "shrinkage_rate_pct": 1.1
    },
    "208": {
        "store_id": "208",
        "total_skus": 3200,
        "out_of_stock_skus": [
            {"sku": "APP-DNM-301", "name": "Vintage Slim Denim Jeans (32x32)", "dept": "Apparel", "lost_sales_est": "$890/week"},
            {"sku": "APP-SWT-102", "name": "Merino Wool Crewneck Sweater (Navy)", "dept": "Apparel", "lost_sales_est": "$1,120/week"},
            {"sku": "ELE-CHG-009", "name": "GaN 65W Fast Wall Charger", "dept": "Electronics", "lost_sales_est": "$650/week"}
        ],
        "low_stock_skus": [
            {"sku": "ELE-TAB-701", "name": "ACME Horizon 11-inch Tablet (128GB)", "dept": "Electronics", "units_left": 3, "reorder_point": 8}
        ],
        "in_stock_rate_pct": 96.1,
        "shrinkage_rate_pct": 1.4
    },
    "315": {
        "store_id": "315",
        "total_skus": 1950,
        "out_of_stock_skus": [
            {"sku": "ELE-SPK-220", "name": "SonicBoom Waterproof Bluetooth Speaker", "dept": "Electronics", "lost_sales_est": "$1,800/week"}
        ],
        "low_stock_skus": [],
        "in_stock_rate_pct": 99.1,
        "shrinkage_rate_pct": 0.8
    }
}


def query_store_sales(store_id: str, date_range: str = "last_30_days") -> Dict[str, Any]:
    """Queries store performance data including revenue, traffic, transactions, labor hours, and department sales.
    
    Args:
        store_id: The ID of the store (e.g. '104', '208', '315').
        date_range: The reporting period: 'yesterday' or 'last_30_days'. Defaults to 'last_30_days'.
    
    Returns:
        Dict containing sales, budget targets, foot traffic, labor hours, and department margins.
    """
    clean_id = str(store_id).strip().replace("#", "")
    store = MOCK_STORE_DATA.get(clean_id)
    if not store:
        # Fallback to Store 104 with clean_id notation
        return {
            "error": f"Store #{store_id} not found in ACME Retail Network. Available test stores: 104 (Downtown), 208 (West Suburbs), 315 (Austin).",
            "available_stores": ["104", "208", "315"]
        }
    
    period_data = store.get(date_range, store["last_30_days"])
    return {
        "store_id": store["store_id"],
        "store_name": store["name"],
        "region": store["region"],
        "format": store["format"],
        "reporting_period": date_range,
        "gross_revenue": period_data["gross_revenue"],
        "target_budget": period_data["target_budget"],
        "foot_traffic": period_data["foot_traffic"],
        "transaction_count": period_data["transaction_count"],
        "labor_hours": period_data["labor_hours"],
        "departments": period_data["departments"]
    }


def query_store_inventory(store_id: str, category: str = "all") -> Dict[str, Any]:
    """Queries inventory health metrics, out-of-stock items, and low-stock alerts for a specific store.
    
    Args:
        store_id: The store ID (e.g. '104', '208', '315').
        category: Filter by department category or 'all'. Defaults to 'all'.
    
    Returns:
        Dict containing in-stock rate, out of stock items, and low stock warnings.
    """
    clean_id = str(store_id).strip().replace("#", "")
    inv = MOCK_INVENTORY_DATA.get(clean_id)
    if not inv:
        return {
            "error": f"Inventory records for Store #{store_id} not found.",
            "available_stores": ["104", "208", "315"]
        }
    return inv


def query_store_metadata(store_id: str) -> Dict[str, Any]:
    """Returns general metadata about an ACME retail store location.
    
    Args:
        store_id: The store ID.
    """
    clean_id = str(store_id).strip().replace("#", "")
    store = MOCK_STORE_DATA.get(clean_id)
    if not store:
        return {"error": f"Store #{store_id} not found."}
    return {
        "store_id": store["store_id"],
        "name": store["name"],
        "region": store["region"],
        "format": store["format"],
        "general_manager": store["manager"]
    }
