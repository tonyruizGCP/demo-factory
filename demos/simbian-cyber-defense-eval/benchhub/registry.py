from typing import List

try:
    from .schema import BenchHubSliceFilter
    from ..core.models import MitreTactic
except (ImportError, ValueError):
    from benchhub.schema import BenchHubSliceFilter
    from core.models import MitreTactic

BENCHMARK_SLICES: List[BenchHubSliceFilter] = [
    BenchHubSliceFilter(
        slice_id="full-benchmark",
        name="Full Enterprise Attack Suite",
        description="Comprehensive evaluation across all 12 MITRE ATT&CK tactics.",
        tags=["comprehensive", "simbian-official"],
    ),
    BenchHubSliceFilter(
        slice_id="apt-multistage-slice",
        name="APT Multi-Stage Intrusions",
        description="Complex nation-state APT campaigns with evasive living-off-the-land techniques.",
        difficulties=["APT-MultiStage", "Hard"],
        tags=["apt", "evasion", "multi-stage"],
    ),
    BenchHubSliceFilter(
        slice_id="credential-lateral-slice",
        name="Credential Access & Lateral Movement",
        description="Scenarios focusing on LSASS dumps, Pass-the-Hash, WMI pivot, and SMB lateral movement.",
        tactics=[MitreTactic.CREDENTIAL_ACCESS, MitreTactic.LATERAL_MOVEMENT],
        tags=["credentials", "mimikatz", "lateral-movement"],
    ),
    BenchHubSliceFilter(
        slice_id="persistence-evasion-slice",
        name="Persistence & Defense Evasion",
        description="Scenarios featuring Registry Run keys, Scheduled tasks, Event log clearing, and LOLBins.",
        tactics=[MitreTactic.PERSISTENCE, MitreTactic.DEFENSE_EVASION],
        tags=["persistence", "evasion", "registry"],
    ),
    BenchHubSliceFilter(
        slice_id="ransomware-impact-slice",
        name="Ransomware & Impact",
        description="Scenarios testing detection of shadow copy deletion (vssadmin), BitLocker encryption, and staging.",
        tactics=[MitreTactic.IMPACT, MitreTactic.COLLECTION, MitreTactic.EXFILTRATION],
        tags=["ransomware", "impact", "vssadmin"],
    ),
]
