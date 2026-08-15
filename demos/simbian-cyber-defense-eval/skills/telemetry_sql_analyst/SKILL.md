---
name: telemetry-sql-analyst
description: Formulates and executes optimized SQLite queries on process creation, network, and registry telemetry tables.
weight: 1.2
role: "Telemetry SQL Analyst"
---

# Skill: Telemetry SQL Analyst

## Purpose
The **Telemetry SQL Analyst** translates investigative hypotheses into robust, performant SQL queries executed directly against the Harbor Sandbox telemetry database (`events` table, `process_creation`, `network_connections`, `persistence_events`, `powershell_scripts`).

## Best Practices & Guidelines
1. **Case-Insensitive Filters**: Always wrap string comparisons with `LOWER(column) LIKE '%keyword%'` or use SQLite `COLLATE NOCASE`.
2. **Broad Net vs. Over-Filtering**: Avoid rigid queries that require 4+ specific AND conditions simultaneously. Instead, filter on core indicators (e.g. `event_id IN (1, 3, 11, 13)` or `command_line LIKE '%-enc%' OR command_line LIKE '%powershell%'`).
3. **Parent-Child Correlation**: Trace process lineages using `parent_process` and `process_name` to establish complete execution ancestry.
4. **Result Limiting**: Always append `LIMIT 50` or `LIMIT 100` to prevent query output buffer bloat.
5. **Wildcard Host & Process Matching**: Use `WHERE host LIKE '%WKSTN%'` or `parent_process LIKE '%WINWORD%'` to account for domain prefixes (e.g. `CORP-WKSTN-01`).
6. **Progressive Kill-Chain Pivot**: As soon as suspicious processes are discovered, pivot to query network sockets (`event_id = 3`), persistence (`event_id = 11, 13`), and LSASS memory access.

