---
name: store-performance-review
description: Conducts an in-depth operational and financial performance review for an ACME Inc retail store. Evaluates revenue vs target, foot-traffic conversion, labor efficiency, department gross margins, and generates prescriptive manager recommendations.
compatibility: "Compatible with ADK 2.x and Retail Data Toolset"
---

# Store Performance Review Skill

This skill defines the standardized protocol for analyzing retail store performance across ACME Inc's store network.

## Target Audience
Store Managers, Assistant Managers, and Regional Operations Directors seeking actionable insights on store health, sales variances, and labor allocation.

## Prerequisites
To execute this skill, the agent must have access to:
- `query_store_sales`: To fetch store revenues, budgets, traffic, and department breakdowns.
- `query_store_inventory`: To cross-examine inventory health and stockout impact.
- `run_skill_script`: To execute the bundled `scripts/calculate_store_kpis.py` script.
- `load_skill_resource`: To inspect the KPI rubric in `references/kpi_benchmarks.md`.

---

## Step-by-Step Diagnostic Workflow

Follow these steps in strict sequence:

### Step 1: Ingest Store Sales Metrics
Call `query_store_sales` using the requested `store_id`. Extract:
- Gross Revenue ($)
- Target Budget ($)
- Total Store Foot Traffic (visitors)
- Transaction Count (receipts)
- Total Labor Hours Scheduled

### Step 2: Compute Core Performance KPIs
Execute the bundled calculation script `scripts/calculate_store_kpis.py` via `run_skill_script` passing:
```json
{
  "revenue": "<gross_revenue>",
  "target": "<target_budget>",
  "traffic": "<foot_traffic>",
  "transactions": "<transaction_count>",
  "labor_hours": "<labor_hours>"
}
```
This script computes:
- Sales Variance vs Budget (%)
- Conversion Rate (%)
- Average Order Value (AOV) ($)
- Sales per Labor Hour (SPLH) ($)

### Step 3: Evaluate Against Corporate Benchmarks
Inspect `references/kpi_benchmarks.md` via `load_skill_resource` and evaluate each metric against target thresholds:
- Conversion: Target ≥ 24.5%
- SPLH: Target ≥ $185.00 / hour
- Variance vs Budget: On-track ≥ 0.0%

### Step 4: Department-Level Deep Dive
Analyze the department breakdown returned by `query_store_sales`:
- Identify top-performing department by margin contribution.
- Identify underperforming department lagging behind budget.
- Check inventory levels for underperforming departments using `query_store_inventory`.

### Step 5: Synthesize the Executive Performance Brief
Format the final output strictly following the layout below:

---

# 🏬 ACME Retail Store Performance Review: Store [Store ID]

## 📊 Performance Scorecard
| Metric | Actual | Target / Benchmark | Status |
| :--- | :--- | :--- | :--- |
| **Gross Revenue** | $[Actual Revenue] | $[Budget Target] | [🟢 Outperforming / 🟡 Near Target / 🔴 Lagging] |
| **Budget Variance** | [+/- X.X%] | 0.0% | [Status] |
| **Conversion Rate** | [X.X%] | ≥ 24.5% | [Status] |
| **Avg Order Value (AOV)** | $[XX.XX] | $[Benchmark] | [Status] |
| **Sales per Labor Hour** | $[XXX.XX] | ≥ $185.00 | [Status] |

## 🔍 Diagnostic Findings
- **Revenue Drivers**: [Key positive contributors to revenue]
- **Operational Friction**: [Labor bottlenecks, traffic conversion leakage, or inventory stockouts]
- **Department Breakdown**: [Highlight highest and lowest margin categories]

## 🎯 High-Impact Action Items (Next 7 Days)
1. **Floor Re-allocation**: [Actionable labor or floor schedule adjustment]
2. **Merchandising Focus**: [Category or promotion priority]
3. **Inventory Remedy**: [Replenishment or stock-transfer recommendation]
