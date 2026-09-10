---
name: daily-summary-recap
description: Generates a concise, high-velocity morning huddle recap for retail store managers. Summarizes yesterday's closing numbers, highlights top category wins, alerts on out-of-stock items, and specifies 3 focus directives for the day.
compatibility: "Compatible with ADK 2.x and Retail Data Toolset"
---

# Daily Summary Recap Skill

This skill formats a punchy, 3-minute morning briefing tailored for ACME Inc store managers and shift supervisors before store opening.

## Target Audience
Store Managers, Assistant Store Managers, Floor Leads, and Shift Supervisors.

## Prerequisites
The executing agent requires:
- `query_store_sales`: To fetch yesterday's sales figures and category sales.
- `query_store_inventory`: To detect critical stockouts on high-velocity items.
- `run_skill_script`: To execute `scripts/generate_huddle_brief.py`.
- `load_skill_resource`: To inspect `references/huddle_template.md`.

---

## Step-by-Step Execution Workflow

1. **Retrieve Yesterday's Metrics**: Call `query_store_sales` with `date_range="yesterday"`.
2. **Scan Critical Inventory**: Call `query_store_inventory` to identify any out-of-stock items in high-traffic departments.
3. **Execute Huddle Compiler Script**: Run `scripts/generate_huddle_brief.py` via `run_skill_script` to calculate the daily pacing against monthly goal.
4. **Format Output**: Format using the standardized morning huddle markdown layout below:

---

# ☀️ Morning Store Huddle: Store [Store ID]

## ⚡ Yesterday's Flash Snapshot
- **Revenue**: $[Yesterday Sales] (Goal: $[Daily Goal] | **[+/- X.X%]**)
- **Transactions**: [Count] transactions @ **$[AOV]** average basket.
- **Star Category**: [Highest selling category] ($[Sales], +[X]% vs benchmark).

## 🚨 Inventory & Floor Alerts
- **Out of Stock**: [List 1-2 critical stockout items requiring replenishment]
- **Markdown / Promo Push**: [Key promotion active on the floor today]

## 🎯 Shift Focus Directives
1. **Goal for Today**: Hit $[Today's Target] with focus on [Category].
2. **Floor Coverage**: Ensure active coverage in [High-traffic department].
3. **Customer Greeting**: Target 100% greeting rate to lift conversion toward 25%.
