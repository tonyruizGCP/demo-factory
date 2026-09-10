---
name: inventory-optimization-audit
description: Audits retail inventory levels, identifying safety-stock breaches, stockout revenue losses, aging stock markdown liabilities, and distribution center replenishment orders for ACME Inc stores.
compatibility: "Compatible with ADK 2.x and Retail Data Toolset"
---

# Inventory Optimization Audit Skill

Provides inventory health diagnostics and automated replenishment recommendations.

## Step-by-Step Workflow
1. **Query Store Inventory**: Use `query_store_inventory` for the target store.
2. **Execute Inventory Risk Audit**: Run `scripts/audit_inventory.py` via `run_skill_script`.
3. **Synthesize Report**:
   - Stockout alerts on high-turnover items.
   - Recommended DC replenishment transfer quantities.
   - Overstock clearance candidates.
