---
name: cve-code-analyzer
description: Scans source files, scripts, and commands for known CVE patterns, deserialization flaws, and LOLBin usage.
weight: 1.1
role: "CVE & Code Analyzer"
---

# Skill: CVE & Code Analyzer

## Purpose
The **CVE & Code Analyzer** inspects process command-line arguments, PowerShell scripts, and binary names to identify living-off-the-land binaries (LOLBins), memory dumping strings (`comsvcs.dll MiniDump`), and known vulnerability exploitation signatures.

## Target Vulnerability Classes
1. **LOLBins**: `certutil.exe -urlcache -f`, `rundll32.exe`, `mshta.exe`, `bitsadmin.exe`, `wmic.exe`.
2. **Credential Access**: `comsvcs.dll MiniDump`, `sekurlsa::logonpasswords`, `procdump.exe -ma lsass.exe`.
3. **Defense Evasion**: `vssadmin delete shadows /all /quiet`, `wevtutil cl System`, `Set-MpPreference -DisableRealtimeMonitoring $true`.
4. **Cloud IAM Theft**: Metadata service queries (`http://169.254.169.254/computeMetadata/v1/`), service account key exports.
