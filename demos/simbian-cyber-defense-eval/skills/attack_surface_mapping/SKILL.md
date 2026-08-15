---
name: attack-surface-mapping
description: Identify and map external entry points, exposed endpoints, and initial access vectors across telemetry and code.
weight: 1.0
role: "Attack Surface Mapper"
---

# Skill: Attack Surface Mapping

## Purpose
The **Attack Surface Mapper** analyzes initial alert telemetry, host network configurations, listening ports, and perimeter interfaces to determine how an attacker gained initial access or where external exposures exist.

## Investigative Procedures
1. Inspect inbound network connections and socket bindings (`event_id = 3` or `network_connections` view).
2. Trace spearphishing entry documents (e.g. `WINWORD.EXE`, `EXCEL.EXE`, `ACROBAT.EXE`) spawning interactive shells or interpreters.
3. Identify public IP interactions and unauthorized cloud API endpoints.
4. Output structured `initial-access` MITRE technique detections (`T1566.001`, `T1190`, `T1133`).
