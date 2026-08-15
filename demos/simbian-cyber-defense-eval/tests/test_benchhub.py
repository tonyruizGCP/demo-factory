"""Unit tests for BenchHub dataset curator and slice registry."""

import pytest
from pathlib import Path
import sys

# Ensure root is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchhub.curator import BenchHubCurator
from core.models import MitreTactic


def test_benchhub_curator_loads_scenarios():
    curator = BenchHubCurator()
    scenarios = curator.list_scenarios()
    assert len(scenarios) >= 4
    
    scenario_ids = [s.id for s in scenarios]
    assert "simbian-apt29-01" in scenario_ids
    assert "simbian-ransomware-01" in scenario_ids
    assert "simbian-cloud-iam-01" in scenario_ids
    assert "simbian-lolbins-01" in scenario_ids


def test_benchhub_slicing():
    curator = BenchHubCurator()
    
    # Test APT multi-stage slice
    apt_slice = curator.filter_scenarios("apt-multistage-slice")
    assert len(apt_slice) >= 1
    assert any(s.attack_family == "APT29" for s in apt_slice)

    # Test Ransomware slice
    ransom_slice = curator.filter_scenarios("ransomware-impact-slice")
    assert len(ransom_slice) >= 1
    assert any(s.attack_family == "Ransomware" for s in ransom_slice)


def test_benchhub_dataset_metadata():
    curator = BenchHubCurator()
    meta = curator.get_dataset_metadata()
    assert meta.total_scenarios >= 4
    assert meta.total_log_events > 0
    assert len(meta.supported_tactics) >= 8
