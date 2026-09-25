"""ATIF Task Schema and Core Contracts for BenchHub.

Defines standardized Pydantic V2 data contracts conforming to the Agent Task/Trajectory
Interchange Format (ATIF) for agentic coding benchmarks, including behavioral capability
taxonomies, difficulty strata, deterministic verification harnesses, and benchmark suites.
"""

from __future__ import annotations

from enum import Enum
from functools import total_ordering
from typing import Any, Dict, Iterator, List, Optional, Set, Union
from pydantic import BaseModel, Field, field_validator, model_validator


class BehavioralTag(str, Enum):
    """Core agentic capabilities exercised by coding benchmark tasks."""
    TOOL_SELECTION = "tool_selection"
    MULTI_STEP_RETRIEVAL = "multi_step_retrieval"
    STATE_MUTATION = "state_mutation"
    CONSTRAINT_ADHERENCE = "constraint_adherence"

    @classmethod
    def _missing_(cls, value: object) -> Optional[BehavioralTag]:
        """Normalize case and hyphenation for resilient dataset ingestion."""
        if isinstance(value, str):
            normalized = value.lower().replace("-", "_").strip()
            for member in cls:
                if member.value == normalized or member.name.lower() == normalized:
                    return member
        return None


@total_ordering
class DifficultyLevel(str, Enum):
    """Discrete task difficulty strata with ordinal comparison support."""
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    EXPERT = "EXPERT"

    @classmethod
    def _missing_(cls, value: object) -> Optional[DifficultyLevel]:
        """Normalize case and whitespace for resilient dataset ingestion."""
        if isinstance(value, str):
            normalized = value.upper().strip()
            for member in cls:
                if member.value == normalized or member.name == normalized:
                    return member
        return None

    @property
    def rank(self) -> int:
        """Ordinal rank for sorting and comparison."""
        _ranks = {
            DifficultyLevel.EASY: 1,
            DifficultyLevel.MEDIUM: 2,
            DifficultyLevel.HARD: 3,
            DifficultyLevel.EXPERT: 4,
        }
        return _ranks[self]

    def __lt__(self, other: object) -> bool:
        if isinstance(other, DifficultyLevel):
            return self.rank < other.rank
        return NotImplemented


class VerificationSpec(BaseModel):
    """Deterministic, reproducible task verification harness specification."""
    command: str = Field(
        ...,
        min_length=1,
        description="Shell command executed to grade the task (e.g. 'pytest tests/test_patch.py')",
    )
    script: Optional[str] = Field(
        default=None,
        description="Optional inline verification script content (e.g. bash or python script)",
    )
    timeout_seconds: float = Field(
        default=60.0,
        gt=0.0,
        le=3600.0,
        description="Watchdog timeout deadline in seconds",
    )
    expected_exit_code: int = Field(
        default=0,
        description="Expected process exit code for passing verification run",
    )
    artifact_paths: List[str] = Field(
        default_factory=list,
        description="List of expected filesystem artifacts that must exist or be modified",
    )
    environment_variables: Dict[str, str] = Field(
        default_factory=dict,
        description="Execution environment variables passed to the verification sandbox",
    )

    @field_validator("command")
    @classmethod
    def validate_non_empty_command(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Verification command must not be empty or whitespace only")
        return s

    @property
    def timeout_sec(self) -> float:
        return self.timeout_seconds


class ATIFTask(BaseModel):
    """Standardized ATIF-compliant benchmark task definition."""
    task_id: str = Field(
        ...,
        min_length=1,
        description="Globally unique deterministic task identifier",
    )
    instruction: str = Field(
        ...,
        min_length=1,
        description="Natural language prompt delivered to the agent under evaluation",
    )
    difficulty: DifficultyLevel = Field(
        ...,
        description="Stratified difficulty stratum",
    )
    behavioral_tags: List[BehavioralTag] = Field(
        default_factory=list,
        description="Agent capability dimensions exercised by this task",
    )
    verification: VerificationSpec = Field(
        ...,
        description="Deterministic grading harness specification",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Domain, language, author, source repository, git commit hashes, etc.",
    )

    @field_validator("task_id")
    @classmethod
    def validate_non_empty_task_id(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("task_id must not be empty or whitespace only")
        return s

    @field_validator("instruction")
    @classmethod
    def validate_non_empty_instruction(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("instruction must not be empty or whitespace only")
        return s

    @field_validator("behavioral_tags")
    @classmethod
    def validate_unique_tags(cls, tags: List[BehavioralTag]) -> List[BehavioralTag]:
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        return sorted(unique_tags, key=lambda t: t.value)

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-like access helper for test compatibility."""
        return getattr(self, key, default)

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item)

    @property
    def composite_stratum_key(self) -> str:
        """Composite key representing the joint difficulty and behavioral capability stratum.

        Example: 'MEDIUM::state_mutation+tool_selection'
        """
        tag_str = "+".join(sorted(t.value for t in self.behavioral_tags))
        return f"{self.difficulty.value}::{tag_str}"

    @property
    def tag_values(self) -> List[str]:
        """Convenience accessor returning behavioral tags as raw string values."""
        return [t.value for t in self.behavioral_tags]

    def has_tag(self, tag: Union[BehavioralTag, str]) -> bool:
        """Check if a specific behavioral tag is present on this task."""
        tag_enum = BehavioralTag(tag) if isinstance(tag, str) else tag
        return tag_enum in self.behavioral_tags

    def __hash__(self) -> int:
        return hash(self.task_id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ATIFTask):
            return self.task_id == other.task_id
        return False


class BenchmarkSuite(BaseModel):
    """Container suite for ATIF benchmark tasks with indexing and filtering capabilities."""
    name: str = Field(
        default="benchmark-suite",
        description="Suite identifier or name (e.g. 'swe-bench-lite-sample')",
    )
    version: str = Field(
        default="1.0.0",
        description="Semantic version string for the benchmark suite release",
    )
    description: str = Field(
        default="",
        description="Human-readable description of benchmark domain and evaluation goals",
    )
    tasks: List[ATIFTask] = Field(
        default_factory=list,
        description="Ordered list of ATIF benchmark tasks",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Suite-level metadata, licensing, and provenance",
    )

    @model_validator(mode="before")
    @classmethod
    def handle_suite_name_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "name" not in data and "suite_name" in data:
                data["name"] = data["suite_name"]
            elif not data.get("name") and data.get("suite_name"):
                data["name"] = data["suite_name"]
        return data

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Suite name must not be empty or whitespace only")
        return s

    @field_validator("tasks")
    @classmethod
    def validate_unique_task_ids(cls, tasks: List[ATIFTask]) -> List[ATIFTask]:
        seen: Set[str] = set()
        duplicates: List[str] = []
        for task in tasks:
            if task.task_id in seen:
                duplicates.append(task.task_id)
            seen.add(task.task_id)
        if duplicates:
            raise ValueError(f"Duplicate task_id(s) found in BenchmarkSuite: {duplicates}")
        return tasks

    @property
    def task_ids(self) -> List[str]:
        """Return all task identifiers present in the suite."""
        return [task.task_id for task in self.tasks]

    @property
    def difficulty_distribution(self) -> Dict[DifficultyLevel, int]:
        """Count of tasks partitioned across each difficulty level."""
        dist = {d: 0 for d in DifficultyLevel}
        for task in self.tasks:
            dist[task.difficulty] += 1
        return dist

    @property
    def tag_distribution(self) -> Dict[BehavioralTag, int]:
        """Count of tasks exercising each behavioral capability tag."""
        dist = {t: 0 for t in BehavioralTag}
        for task in self.tasks:
            for tag in task.behavioral_tags:
                dist[tag] += 1
        return dist

    def get_task(self, task_id: str) -> Optional[ATIFTask]:
        """Retrieve a task by its task_id, or None if not present."""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def filter_by_tag(self, tag: Union[BehavioralTag, str]) -> List[ATIFTask]:
        """Return tasks that exercise the specified behavioral capability."""
        tag_enum = BehavioralTag(tag) if isinstance(tag, str) else tag
        return [t for t in self.tasks if tag_enum in t.behavioral_tags]

    def filter_by_difficulty(self, difficulty: Union[DifficultyLevel, str]) -> List[ATIFTask]:
        """Return tasks that match the specified difficulty level."""
        diff_enum = DifficultyLevel(difficulty) if isinstance(difficulty, str) else difficulty
        return [t for t in self.tasks if t.difficulty == diff_enum]

    def get_strata(self) -> Dict[str, List[ATIFTask]]:
        """Group tasks by their composite stratum key (difficulty + sorted behavioral tags)."""
        strata: Dict[str, List[ATIFTask]] = {}
        for task in self.tasks:
            key = task.composite_stratum_key
            strata.setdefault(key, []).append(task)
        return strata

    def add_task(self, task: ATIFTask) -> None:
        """Add a task to the suite, verifying task_id uniqueness."""
        if self.get_task(task.task_id) is not None:
            raise ValueError(f"Task with task_id '{task.task_id}' already exists in suite '{self.name}'")
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> Optional[ATIFTask]:
        """Remove and return a task by its task_id, or None if not found."""
        for i, task in enumerate(self.tasks):
            if task.task_id == task_id:
                return self.tasks.pop(i)
        return None

    def __len__(self) -> int:
        return len(self.tasks)

    def __iter__(self) -> Iterator[ATIFTask]:
        return iter(self.tasks)

    def __getitem__(self, key: Union[int, str]) -> ATIFTask:
        """Index by integer position or string task_id."""
        if isinstance(key, int):
            return self.tasks[key]
        elif isinstance(key, str):
            task = self.get_task(key)
            if task is None:
                raise KeyError(f"Task with task_id '{key}' not found in suite '{self.name}'")
            return task
        raise TypeError(f"Index must be int or str, got {type(key).__name__}")

    def __contains__(self, item: Union[str, ATIFTask]) -> bool:
        if isinstance(item, str):
            return self.get_task(item) is not None
        elif isinstance(item, ATIFTask):
            return item.task_id in set(self.task_ids)
        return False
