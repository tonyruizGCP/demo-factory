---
name: false-positive-pruner
description: Identifies and filters benign administrative activity, developer scripts, and non-malicious anomalies.
weight: 1.0
role: "False Positive Pruner"
---

# Skill: False Positive Pruner

## Purpose
The **False Positive Pruner** eliminates noise and reduces the False Discovery Rate (FDR) by differentiating between malicious activity and authorized system maintenance.

## Filtering Rules
1. Distinguish between developer builds / IT automation (e.g. SCCM, Windows Update, authorized CI runners) and attacker LOLBins.
2. Verify if processes were executed by privileged service accounts with expected parentage.
3. Suppress low-confidence detections that lack corroborating network, file, or registry telemetry.
