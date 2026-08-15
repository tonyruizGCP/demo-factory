"""BenchHub dataset curator and filter engine for cyber security benchmarks.

Provides automated dataset slicing, difficulty filtering, tactic filtering,
and unified benchmark dataset compilation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional
try:
    from ..core.models import MitreTactic, ScenarioTask
    from .schema import BenchHubDatasetMetadata, BenchHubSliceFilter
except (ImportError, ValueError):
    from core.models import MitreTactic, ScenarioTask
    from benchhub.schema import BenchHubDatasetMetadata, BenchHubSliceFilter


class BenchHubCurator:
    """Unified curation and filtering engine for Cyber Defense Benchmark datasets."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or (Path(__file__).parent.parent / "data" / "scenarios")
        self._scenarios: Dict[str, ScenarioTask] = {}
        self._slices: Dict[str, BenchHubSliceFilter] = {}
        self._init_default_slices()
        self.load_scenarios()

    def _init_default_slices(self) -> None:
        """Register default BenchHub evaluation slices."""
        default_slices = [
            BenchHubSliceFilter(
                slice_id="full-benchmark",
                name="Full Enterprise Attack Suite",
                description="Comprehensive evaluation across all 12 MITRE ATT&CK tactics with high-fidelity intrusion scenarios.",
                tags=["comprehensive", "full-suite", "simbian-official"],
            ),
            BenchHubSliceFilter(
                slice_id="apt-multistage-slice",
                name="APT Multi-Stage Intrusions",
                description="Complex nation-state APT campaigns with evasive living-off-the-land techniques.",
                difficulties=["APT-MultiStage", "Hard"],
                attack_families=["APT29", "APT28", "Cloud-IAM"],
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
        for s in default_slices:
            self._slices[s.slice_id] = s

    def register_scenario(self, scenario: ScenarioTask) -> None:
        """Register a scenario task into the BenchHub catalog."""
        self._scenarios[scenario.id] = scenario

    def load_scenarios(self) -> int:
        """Load scenario JSON definitions from the data directory."""
        if not self.data_dir.exists():
            return 0

        count = 0
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    scenario = ScenarioTask(**data)
                    self.register_scenario(scenario)
                    count += 1
            except Exception as err:
                print(f"[BenchHub] Warning: Failed to load {file_path}: {err}")
        return count

    def get_scenario(self, scenario_id: str) -> Optional[ScenarioTask]:
        """Retrieve a specific scenario by ID."""
        return self._scenarios.get(scenario_id)

    def list_scenarios(self) -> List[ScenarioTask]:
        """List all loaded scenarios."""
        return list(self._scenarios.values())

    def list_slices(self) -> List[BenchHubSliceFilter]:
        """List all available BenchHub slices."""
        return list(self._slices.values())

    def get_slice(self, slice_id: str) -> Optional[BenchHubSliceFilter]:
        """Retrieve a slice definition by ID."""
        return self._slices.get(slice_id)

    def filter_scenarios(self, slice_id: str) -> List[ScenarioTask]:
        """Filter scenarios matching a specified BenchHub slice."""
        slice_spec = self._slices.get(slice_id)
        if not slice_spec:
            return list(self._scenarios.values())

        matched: List[ScenarioTask] = []
        for sc in self._scenarios.values():
            # Check difficulty filter
            if slice_spec.difficulties and sc.difficulty not in slice_spec.difficulties:
                continue

            # Check attack family filter
            if slice_spec.attack_families and sc.attack_family not in slice_spec.attack_families:
                continue

            # Check tactics filter
            if slice_spec.tactics:
                has_tactic = any(t in sc.tactics_present for t in slice_spec.tactics)
                if not has_tactic:
                    continue

            # Check event count bounds
            if slice_spec.min_event_count and sc.total_events < slice_spec.min_event_count:
                continue
            if slice_spec.max_event_count and sc.total_events > slice_spec.max_event_count:
                continue

            matched.append(sc)
        return matched

    def get_dataset_metadata(self) -> BenchHubDatasetMetadata:
        """Compile aggregate metadata across the curated dataset."""
        all_tactics = set()
        total_events = 0
        for sc in self._scenarios.values():
            for t in sc.tactics_present:
                all_tactics.add(t.value)
            total_events += sc.total_events or len(sc.events)

        return BenchHubDatasetMetadata(
            total_scenarios=len(self._scenarios),
            total_log_events=total_events,
            supported_tactics=sorted(list(all_tactics)),
            slices=list(self._slices.values()),
        )
