"""MITRE ATT&CK Matrix definitions, taxonomy, and helper utilities.

Provides mappings for all 12 enterprise tactics evaluated in Simbian Cyber Defense Benchmark,
plus common technique identifiers, descriptions, and color indicators.
"""

from typing import Dict, List, Optional
from .models import MitreTactic, MitreTechnique

# MITRE ATT&CK Enterprise Tactic Metadata
TACTIC_METADATA: Dict[MitreTactic, Dict[str, str]] = {
    MitreTactic.INITIAL_ACCESS: {
        "id": "TA0001",
        "name": "Initial Access",
        "color": "#EF4444",
        "description": "Techniques used by adversaries to gain an initial foothold within your network.",
        "icon": "🚪",
    },
    MitreTactic.EXECUTION: {
        "id": "TA0002",
        "name": "Execution",
        "color": "#F97316",
        "description": "Techniques that result in adversary-controlled code running on a local or remote system.",
        "icon": "⚡",
    },
    MitreTactic.PERSISTENCE: {
        "id": "TA0003",
        "name": "Persistence",
        "color": "#F59E0B",
        "description": "Techniques adversaries use to keep access across restarts, changed credentials, and interruptions.",
        "icon": "⚓",
    },
    MitreTactic.PRIVILEGE_ESCALATION: {
        "id": "TA0004",
        "name": "Privilege Escalation",
        "color": "#EAB308",
        "description": "Techniques adversaries use to gain higher-level permissions on a system or network.",
        "icon": "📈",
    },
    MitreTactic.DEFENSE_EVASION: {
        "id": "TA0005",
        "name": "Defense Evasion",
        "color": "#84CC16",
        "description": "Techniques adversaries use to avoid detection throughout their compromise.",
        "icon": "🥷",
    },
    MitreTactic.CREDENTIAL_ACCESS: {
        "id": "TA0006",
        "name": "Credential Access",
        "color": "#10B981",
        "description": "Techniques for stealing credentials like account names and passwords.",
        "icon": "🔑",
    },
    MitreTactic.DISCOVERY: {
        "id": "TA0007",
        "name": "Discovery",
        "color": "#06B6D4",
        "description": "Techniques an adversary may use to gain knowledge about the system and internal network.",
        "icon": "🔍",
    },
    MitreTactic.LATERAL_MOVEMENT: {
        "id": "TA0008",
        "name": "Lateral Movement",
        "color": "#3B82F6",
        "description": "Techniques adversaries use to enter and control remote systems on a network.",
        "icon": "↔️",
    },
    MitreTactic.COLLECTION: {
        "id": "TA0009",
        "name": "Collection",
        "color": "#6366F1",
        "description": "Techniques adversaries may use to gather information and sources of information.",
        "icon": "📦",
    },
    MitreTactic.COMMAND_AND_CONTROL: {
        "id": "TA0011",
        "name": "Command and Control",
        "color": "#8B5CF6",
        "description": "Techniques adversaries use to communicate with systems under their control.",
        "icon": "📡",
    },
    MitreTactic.EXFILTRATION: {
        "id": "TA0010",
        "name": "Exfiltration",
        "color": "#D946EF",
        "description": "Techniques adversaries use to steal data from your network.",
        "icon": "📤",
    },
    MitreTactic.IMPACT: {
        "id": "TA0040",
        "name": "Impact",
        "color": "#EC4899",
        "description": "Techniques adversaries use to disrupt availability or compromise integrity.",
        "icon": "💥",
    },
}

# Common MITRE ATT&CK Techniques catalog
COMMON_TECHNIQUES: List[MitreTechnique] = [
    # Initial Access
    MitreTechnique(technique_id="T1566.001", name="Spearphishing Attachment", tactic=MitreTactic.INITIAL_ACCESS, description="Adversary sends spearphishing email with malicious attachment."),
    MitreTechnique(technique_id="T1566.002", name="Spearphishing Link", tactic=MitreTactic.INITIAL_ACCESS, description="Adversary sends spearphishing email with malicious link."),
    MitreTechnique(technique_id="T1190", name="Exploit Public-Facing Application", tactic=MitreTactic.INITIAL_ACCESS, description="Adversary exploits web server or gateway vulnerability."),
    MitreTechnique(technique_id="T1078", name="Valid Accounts", tactic=MitreTactic.INITIAL_ACCESS, description="Adversary leverages compromised legitimate credentials."),

    # Execution
    MitreTechnique(technique_id="T1059.001", name="PowerShell", tactic=MitreTactic.EXECUTION, description="Execution of malicious PowerShell commands or scripts."),
    MitreTechnique(technique_id="T1059.003", name="Windows Command Shell", tactic=MitreTactic.EXECUTION, description="Execution via cmd.exe."),
    MitreTechnique(technique_id="T1059.005", name="Visual Basic", tactic=MitreTactic.EXECUTION, description="VBScript / macro execution."),
    MitreTechnique(technique_id="T1204.002", name="Malicious File Execution", tactic=MitreTactic.EXECUTION, description="User or automated trigger executing malicious binary."),
    MitreTechnique(technique_id="T1047", name="Windows Management Instrumentation (WMI)", tactic=MitreTactic.EXECUTION, description="Execution of commands or binaries using wmic or WMI subscriptions."),

    # Persistence
    MitreTechnique(technique_id="T1547.001", name="Registry Run Keys / Startup Folder", tactic=MitreTactic.PERSISTENCE, description="Modifying Run / RunOnce registry keys for autostart."),
    MitreTechnique(technique_id="T1053.005", name="Scheduled Task", tactic=MitreTactic.PERSISTENCE, description="Creating scheduled tasks via schtasks.exe."),
    MitreTechnique(technique_id="T1543.003", name="Windows Service Creation", tactic=MitreTactic.PERSISTENCE, description="Creating malicious system services."),
    MitreTechnique(technique_id="T1505.003", name="Web Shell", tactic=MitreTactic.PERSISTENCE, description="Backdoor planted on web server file system."),

    # Privilege Escalation
    MitreTechnique(technique_id="T1548.002", name="Bypass User Account Control", tactic=MitreTactic.PRIVILEGE_ESCALATION, description="Elevating process rights via UAC bypass techniques."),
    MitreTechnique(technique_id="T1055.001", name="Dynamic-link Library Injection", tactic=MitreTactic.PRIVILEGE_ESCALATION, description="Injecting malicious DLL into trusted process."),
    MitreTechnique(technique_id="T1068", name="Exploitation for Privilege Escalation", tactic=MitreTactic.PRIVILEGE_ESCALATION, description="Exploiting kernel or service vulnerability to gain SYSTEM."),

    # Defense Evasion
    MitreTechnique(technique_id="T1027", name="Obfuscated Files or Information", tactic=MitreTactic.DEFENSE_EVASION, description="Base64, XOR, or encrypted payload strings."),
    MitreTechnique(technique_id="T1070.001", name="Clear Windows Event Logs", tactic=MitreTactic.DEFENSE_EVASION, description="Using wevtutil to clear security audit logs."),
    MitreTechnique(technique_id="T1562.001", name="Disable or Modify Tools (AV/EDR)", tactic=MitreTactic.DEFENSE_EVASION, description="Stopping Windows Defender or tampering with Sysmon."),
    MitreTechnique(technique_id="T1218.011", name="Rundll32 Execution", tactic=MitreTactic.DEFENSE_EVASION, description="Using rundll32.exe LOLBin to proxy code execution."),
    MitreTechnique(technique_id="T1105", name="Ingress Tool Transfer (certutil/bitsadmin)", tactic=MitreTactic.DEFENSE_EVASION, description="Downloading second-stage payloads via certutil -urlcache."),

    # Credential Access
    MitreTechnique(technique_id="T1003.001", name="LSASS Memory Dump", tactic=MitreTactic.CREDENTIAL_ACCESS, description="Dumping lsass.exe process memory (e.g. procdump, mimikatz, comsvcs.dll)."),
    MitreTechnique(technique_id="T1003.002", name="Security Account Manager (SAM) Dump", tactic=MitreTactic.CREDENTIAL_ACCESS, description="Extracting password hashes from SAM registry hive."),
    MitreTechnique(technique_id="T1555", name="Credentials from Password Stores", tactic=MitreTactic.CREDENTIAL_ACCESS, description="Stealing credentials from browser caches or credential vault."),

    # Discovery
    MitreTechnique(technique_id="T1087.001", name="Local Account Discovery (net user)", tactic=MitreTactic.DISCOVERY, description="Querying local accounts on the system."),
    MitreTechnique(technique_id="T1087.002", name="Domain Account Discovery (net group)", tactic=MitreTactic.DISCOVERY, description="Enumerating active directory domain accounts and admins."),
    MitreTechnique(technique_id="T1083", name="File and Directory Discovery", tactic=MitreTactic.DISCOVERY, description="Searching filesystem for sensitive files or shares."),
    MitreTechnique(technique_id="T1049", name="System Network Connections Discovery (netstat)", tactic=MitreTactic.DISCOVERY, description="Querying active network sockets and sessions."),
    MitreTechnique(technique_id="T1018", name="Remote System Discovery", tactic=MitreTactic.DISCOVERY, description="Locating other reachable network endpoints."),

    # Lateral Movement
    MitreTechnique(technique_id="T1021.002", name="SMB / Windows Admin Shares", tactic=MitreTactic.LATERAL_MOVEMENT, description="Connecting to remote C$, ADMIN$ shares or PsExec service."),
    MitreTechnique(technique_id="T1021.001", name="Remote Desktop Protocol (RDP)", tactic=MitreTactic.LATERAL_MOVEMENT, description="Lateral movement via RDP session."),
    MitreTechnique(technique_id="T1047", name="Remote WMI Execution", tactic=MitreTactic.LATERAL_MOVEMENT, description="Invoking process creation on remote machine via WMI."),

    # Collection
    MitreTechnique(technique_id="T1560.001", name="Archive via Utility (ZIP/7z)", tactic=MitreTactic.COLLECTION, description="Compressing gathered data prior to exfiltration."),
    MitreTechnique(technique_id="T1114.001", name="Email Collection (PST/OST)", tactic=MitreTactic.COLLECTION, description="Extracting corporate mailbox archives."),
    MitreTechnique(technique_id="T1005", name="Data from Local System", tactic=MitreTactic.COLLECTION, description="Harvesting files from user directories."),

    # Command & Control
    MitreTechnique(technique_id="T1071.001", name="Web Protocols (HTTP/HTTPS C2)", tactic=MitreTactic.COMMAND_AND_CONTROL, description="Beaconing over HTTPS port 443 with encrypted payloads."),
    MitreTechnique(technique_id="T1573.002", name="Asymmetric Cryptography C2", tactic=MitreTactic.COMMAND_AND_CONTROL, description="Encrypted communication channel with external server."),
    MitreTechnique(technique_id="T1090", name="Proxy / SOCKS Tunnel", tactic=MitreTactic.COMMAND_AND_CONTROL, description="Routing traffic through internal proxy bounce points."),

    # Exfiltration
    MitreTechnique(technique_id="T1048.003", name="Exfiltration Over Unencrypted/HTTPS Protocol", tactic=MitreTactic.EXFILTRATION, description="Uploading staged ZIP archive to remote server or cloud storage."),
    MitreTechnique(technique_id="T1567.002", name="Exfiltration to Cloud Storage (GCS/S3)", tactic=MitreTactic.EXFILTRATION, description="Transferring stolen data directly to unauthorized cloud buckets."),

    # Impact
    MitreTechnique(technique_id="T1490", name="Inhibit System Recovery (vssadmin delete shadows)", tactic=MitreTactic.IMPACT, description="Deleting volume shadow copies to prevent file restoration."),
    MitreTechnique(technique_id="T1486", name="Data Encrypted for Impact (Ransomware)", tactic=MitreTactic.IMPACT, description="Encrypting files to demand extortion payment."),
    MitreTechnique(technique_id="T1489", name="Service Stop", tactic=MitreTactic.IMPACT, description="Stopping critical business services or databases."),
]

TECHNIQUE_MAP: Dict[str, MitreTechnique] = {t.technique_id: t for t in COMMON_TECHNIQUES}


def get_tactic_metadata(tactic: MitreTactic) -> Dict[str, str]:
    """Retrieve metadata dictionary for a MITRE tactic."""
    return TACTIC_METADATA.get(tactic, {
        "id": "TA0000",
        "name": tactic.value.replace("-", " ").title(),
        "color": "#64748B",
        "description": "Enterprise tactic category.",
        "icon": "🛡️",
    })


def get_all_tactics() -> List[MitreTactic]:
    """Get all 12 enterprise tactics in canonical attack lifecycle order."""
    return [
        MitreTactic.INITIAL_ACCESS,
        MitreTactic.EXECUTION,
        MitreTactic.PERSISTENCE,
        MitreTactic.PRIVILEGE_ESCALATION,
        MitreTactic.DEFENSE_EVASION,
        MitreTactic.CREDENTIAL_ACCESS,
        MitreTactic.DISCOVERY,
        MitreTactic.LATERAL_MOVEMENT,
        MitreTactic.COLLECTION,
        MitreTactic.COMMAND_AND_CONTROL,
        MitreTactic.EXFILTRATION,
        MitreTactic.IMPACT,
    ]


def lookup_technique(technique_id: str) -> Optional[MitreTechnique]:
    """Lookup technique by ID (e.g. T1059.001)."""
    return TECHNIQUE_MAP.get(technique_id)
