---
name: mitre-attack-classifier
description: Classifies confirmed forensic indicators into official MITRE ATT&CK enterprise tactics and sub-techniques.
weight: 1.3
role: "MITRE ATT&CK Specialist"
---

# Skill: MITRE ATT&CK Classifier

## Purpose
The **MITRE ATT&CK Specialist** maps observed behaviors and telemetry anomalies to the 12 MITRE Enterprise Tactics:
1. `initial-access`
2. `execution`
3. `persistence`
4. `privilege-escalation`
5. `defense-evasion`
6. `credential-access`
7. `discovery`
8. `lateral-movement`
9. `collection`
10. `command-and-control`
11. `exfiltration`
12. `impact`

## Classification Standards
- Ensure each detection includes standard MITRE Technique IDs (e.g. `T1059.001` for PowerShell, `T1003.001` for LSASS Dumping, `T1071.001` for Web Protocols).
- Assign an objective `confidence` score (0.0 to 1.0) and attach all associated `evidence_event_ids`.
