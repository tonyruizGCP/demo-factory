"""BenchHub schema adapter for unified dataset curation and metadata specification.

Implements the BenchHub philosophy (rladmstn1714/BenchHub) for structured
dataset classification, filtering criteria, and benchmark task registration.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
try:
    from ..core.models import MitreTactic
except (ImportError, ValueError):
    from core.models import MitreTactic


class BenchHubSliceFilter(BaseModel):
    """Specification for filtering benchmark datasets into targeted evaluation slices."""
    slice_id: str = Field(..., description="Unique slice identifier (e.g. 'mitre-persistence-slice')")
    name: str = Field(..., description="Human-readable slice title")
    description: str = Field(default="", description="Description of the test objective")
    tactics: Optional[List[MitreTactic]] = Field(default=None, description="Filter by present MITRE tactics")
    difficulties: Optional[List[str]] = Field(default=None, description="Filter by difficulty levels")
    attack_families: Optional[List[str]] = Field(default=None, description="Filter by attack families (e.g. APT, Ransomware)")
    min_event_count: Optional[int] = Field(default=None, description="Minimum log events threshold")
    max_event_count: Optional[int] = Field(default=None, description="Maximum log events threshold")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")


class BenchHubDatasetMetadata(BaseModel):
    """Metadata conforming to BenchHub unified dataset specifications."""
    benchmark_name: str = "Simbian Cyber Defense Benchmark"
    version: str = "1.0.0"
    source_repository: str = "https://github.com/simbianai/cyber_defense_benchmark"
    domain: str = "Cybersecurity / Threat Hunting / SOC Operations"
    total_scenarios: int = 0
    total_log_events: int = 0
    supported_tactics: List[str] = Field(default_factory=list)
    curator: str = "BenchHub Unified Curation Engine"
    slices: List[BenchHubSliceFilter] = Field(default_factory=list)
