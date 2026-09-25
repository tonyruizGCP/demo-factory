"""Benchmark Ingestion Suite Loader for BenchHub.

Provides robust, multi-format (JSON, YAML, Multi-doc YAML) benchmark task ingestion,
directory traversal, duplicate detection, schema validation, and serialization helpers.
"""

from __future__ import annotations

from enum import Enum
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import yaml

from pydantic import ValidationError

from .schema import ATIFTask, BehavioralTag, BenchmarkSuite, DifficultyLevel

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Exceptions & Policies
# -----------------------------------------------------------------------------

class BenchHubError(Exception):
    """Base exception for all BenchHub operations."""
    pass


class SuiteLoadError(BenchHubError):
    """Raised when reading, decoding, or parsing a suite file fails."""
    def __init__(
        self,
        message: str,
        file_path: Optional[Union[Path, str]] = None,
        cause: Optional[Exception] = None,
    ):
        full_msg = f"{message} (file: '{file_path}')" if file_path else message
        if cause:
            full_msg += f" Caused by: {type(cause).__name__}: {cause}"
        super().__init__(full_msg)
        self.file_path = str(file_path) if file_path else None
        self.cause = cause


class DuplicateTaskError(BenchHubError, ValueError):
    """Raised when duplicate task_ids are detected and collision policy is RAISE."""
    def __init__(
        self,
        task_id: str,
        existing_source: Optional[str] = None,
        new_source: Optional[str] = None,
    ):
        msg = f"Duplicate task_id '{task_id}' detected"
        if existing_source and new_source:
            msg += f" (first seen in '{existing_source}', duplicate in '{new_source}')"
        super().__init__(msg)
        self.task_id = task_id
        self.existing_source = existing_source
        self.new_source = new_source


class SuiteValidationError(BenchHubError, ValueError):
    """Raised when ATIF tasks or suites fail schema validation under strict=True."""
    def __init__(self, message: str, errors: Optional[List[str]] = None):
        full_msg = message
        if errors:
            full_msg += f" Violations: {'; '.join(errors)}"
        super().__init__(full_msg)
        self.errors = errors or []


class DuplicatePolicy(str, Enum):
    """Action to take when a duplicate task_id is encountered during ingestion."""
    RAISE = "raise"
    OVERWRITE = "overwrite"
    IGNORE = "ignore"

    @classmethod
    def _missing_(cls, value: object) -> Optional[DuplicatePolicy]:
        if isinstance(value, str):
            norm = value.lower().strip()
            for m in cls:
                if m.value == norm:
                    return m
        return None


# -----------------------------------------------------------------------------
# Core Ingestion Functions
# -----------------------------------------------------------------------------

def parse_task_dict(data: Dict[str, Any], source: str = "<memory>") -> ATIFTask:
    """Parse a single raw dictionary into an ATIFTask model."""
    try:
        return ATIFTask.model_validate(data)
    except ValidationError as err:
        error_msgs = [f"{e['loc']}: {e['msg']}" for e in err.errors()]
        raise SuiteValidationError(
            f"Validation failed for task from '{source}'", errors=error_msgs
        ) from err


def load_suite_from_file(
    file_path: Union[str, Path],
    name: Optional[str] = None,
    on_duplicate: Union[str, DuplicatePolicy] = DuplicatePolicy.RAISE,
    strict: bool = True,
) -> BenchmarkSuite:
    """Ingest a single benchmark file (.json, .yaml, .yml).

    Supports:
    - Full BenchmarkSuite JSON/YAML
    - Single ATIFTask JSON/YAML
    - List of ATIFTasks JSON/YAML
    - Multi-document YAML (--- separated)
    """
    if isinstance(file_path, str) and not file_path.strip():
        raise SuiteLoadError("Target string cannot be empty or whitespace only", file_path=file_path)
    path = Path(file_path)
    if not path.is_file():
        raise SuiteLoadError(f"File not found or is not a regular file: '{path}'", file_path=path)

    dup_policy = DuplicatePolicy(on_duplicate)
    suffix = path.suffix.lower()

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        raise SuiteLoadError(f"Failed to read file: {e}", file_path=path, cause=e) from e

    raw_documents: List[Any] = []
    if suffix == ".json":
        try:
            parsed = json.loads(content)
            raw_documents.append(parsed)
        except json.JSONDecodeError as err:
            raise SuiteLoadError(f"Malformed JSON syntax: {err}", file_path=path, cause=err) from err
    elif suffix in (".yaml", ".yml"):
        try:
            docs = list(yaml.safe_load_all(content))
            raw_documents.extend(d for d in docs if d is not None)
        except yaml.YAMLError as err:
            raise SuiteLoadError(f"Malformed YAML syntax: {err}", file_path=path, cause=err) from err
    else:
        try:
            raw_documents.append(json.loads(content))
        except Exception:
            try:
                docs = list(yaml.safe_load_all(content))
                raw_documents.extend(d for d in docs if d is not None)
            except Exception as err:
                raise SuiteLoadError(f"Unsupported file format and failed parsing: {err}", file_path=path, cause=err) from err

    task_map: Dict[str, Tuple[ATIFTask, str]] = {}
    suite_metadata: Dict[str, Any] = {}
    suite_name = name or path.stem
    suite_version = "1.0.0"
    suite_desc = ""

    for doc in raw_documents:
        if isinstance(doc, dict) and "tasks" in doc:
            suite_name = name or doc.get("name", suite_name)
            suite_version = doc.get("version", suite_version)
            suite_desc = doc.get("description", suite_desc)
            suite_metadata.update(doc.get("metadata", {}))
            raw_tasks = doc.get("tasks", [])
        elif isinstance(doc, list):
            raw_tasks = doc
        elif isinstance(doc, dict):
            raw_tasks = [doc]
        else:
            if strict:
                raise SuiteLoadError(f"Unexpected document structure type '{type(doc).__name__}'", file_path=path)
            continue

        for item in raw_tasks:
            if not isinstance(item, dict):
                if strict:
                    raise SuiteLoadError(f"Expected task dictionary, got '{type(item).__name__}'", file_path=path)
                continue
            try:
                task = parse_task_dict(item, source=str(path))
            except SuiteValidationError:
                if strict:
                    raise
                logger.warning("Skipping invalid task in '%s'", path)
                continue

            if task.task_id in task_map:
                orig_task, orig_src = task_map[task.task_id]
                if dup_policy == DuplicatePolicy.RAISE:
                    raise DuplicateTaskError(task.task_id, existing_source=orig_src, new_source=str(path))
                elif dup_policy == DuplicatePolicy.OVERWRITE:
                    task_map[task.task_id] = (task, str(path))
                elif dup_policy == DuplicatePolicy.IGNORE:
                    continue
            else:
                task_map[task.task_id] = (task, str(path))

    tasks = [t for t, _ in task_map.values()]
    return BenchmarkSuite(
        name=suite_name,
        version=suite_version,
        description=suite_desc,
        tasks=tasks,
        metadata=suite_metadata,
    )


def load_suite_from_directory(
    dir_path: Union[str, Path],
    name: Optional[str] = None,
    recursive: bool = True,
    pattern: Optional[str] = None,
    on_duplicate: Union[str, DuplicatePolicy] = DuplicatePolicy.RAISE,
    strict: bool = True,
) -> BenchmarkSuite:
    """Recursively or flatly ingest all benchmark tasks from a directory.

    Files are discovered and processed in deterministic sorted order.
    """
    if isinstance(dir_path, str) and not dir_path.strip():
        raise SuiteLoadError("Target string cannot be empty or whitespace only", file_path=dir_path)
    directory = Path(dir_path)
    if not directory.is_dir():
        raise SuiteLoadError(f"Directory not found or is not a directory: '{directory}'", file_path=directory)

    dup_policy = DuplicatePolicy(on_duplicate)
    suite_name = name or directory.name

    candidate_files: List[Path] = []
    if pattern:
        glob_fn = directory.rglob if recursive else directory.glob
        candidate_files = list(glob_fn(pattern))
    else:
        patterns = ["*.json", "*.yaml", "*.yml"]
        for pat in patterns:
            glob_fn = directory.rglob if recursive else directory.glob
            candidate_files.extend(glob_fn(pat))

    candidate_files = sorted(set(candidate_files), key=lambda p: str(p))

    task_map: Dict[str, Tuple[ATIFTask, str]] = {}
    suite_metadata: Dict[str, Any] = {"source_directory": str(directory.resolve())}

    for file_path in candidate_files:
        try:
            sub_suite = load_suite_from_file(
                file_path=file_path,
                on_duplicate=dup_policy,
                strict=strict,
            )
        except Exception as e:
            if strict:
                raise
            logger.warning("Failed to load '%s' in permissive mode: %s", file_path, e)
            continue

        for task in sub_suite.tasks:
            if task.task_id in task_map:
                orig_task, orig_src = task_map[task.task_id]
                if dup_policy == DuplicatePolicy.RAISE:
                    raise DuplicateTaskError(task.task_id, existing_source=orig_src, new_source=str(file_path))
                elif dup_policy == DuplicatePolicy.OVERWRITE:
                    task_map[task.task_id] = (task, str(file_path))
                elif dup_policy == DuplicatePolicy.IGNORE:
                    continue
            else:
                task_map[task.task_id] = (task, str(file_path))

    tasks = [t for t, _ in task_map.values()]
    return BenchmarkSuite(
        name=suite_name,
        tasks=tasks,
        metadata=suite_metadata,
    )


def load_suite(
    target: Union[str, Path, Dict[str, Any], Sequence[Dict[str, Any]]],
    name: Optional[str] = None,
    recursive: bool = True,
    pattern: Optional[str] = None,
    on_duplicate: Union[str, DuplicatePolicy] = DuplicatePolicy.RAISE,
    strict: bool = True,
) -> BenchmarkSuite:
    """Polymorphic entrypoint for benchmark ingestion."""
    dup_policy = DuplicatePolicy(on_duplicate)

    if isinstance(target, str):
        if not target.strip():
            raise SuiteLoadError("Target string cannot be empty or whitespace only", file_path=target)
        trimmed = target.strip()
        if trimmed.startswith(("{", "[")):
            return load_suite_from_json_string(trimmed, name=name, on_duplicate=dup_policy, strict=strict)
        if "\n" in trimmed:
            return load_suite_from_yaml_string(trimmed, name=name, on_duplicate=dup_policy, strict=strict)
        # Single line string could be a path or a yaml string
        try:
            p = Path(target)
            if p.exists():
                if p.is_dir():
                    return load_suite_from_directory(
                        p, name=name, recursive=recursive, pattern=pattern, on_duplicate=dup_policy, strict=strict
                    )
                elif p.is_file():
                    return load_suite_from_file(p, name=name, on_duplicate=dup_policy, strict=strict)
        except OSError:
            pass

        # Try parsing as YAML/JSON if path didn't exist
        try:
            return load_suite_from_yaml_string(trimmed, name=name, on_duplicate=dup_policy, strict=strict)
        except Exception:
            pass

        raise SuiteLoadError(f"File not found: '{target}'", file_path=target)

    elif isinstance(target, Path):
        try:
            if target.is_dir():
                return load_suite_from_directory(
                    target, name=name, recursive=recursive, pattern=pattern, on_duplicate=dup_policy, strict=strict
                )
            elif target.is_file():
                return load_suite_from_file(target, name=name, on_duplicate=dup_policy, strict=strict)
        except OSError:
            pass
        raise SuiteLoadError(f"File not found: '{target}'", file_path=target)

    elif isinstance(target, dict):
        return load_suite_from_dict(target, name=name, on_duplicate=dup_policy, strict=strict)

    elif isinstance(target, (list, tuple)):
        return load_suite_from_list(target, name=name, on_duplicate=dup_policy, strict=strict)

    raise TypeError(f"Unsupported target type for load_suite: {type(target).__name__}")


def load_suite_from_dict(
    data: Dict[str, Any],
    name: Optional[str] = None,
    on_duplicate: Union[str, DuplicatePolicy] = DuplicatePolicy.RAISE,
    strict: bool = True,
) -> BenchmarkSuite:
    """Ingest a suite from an in-memory dictionary."""
    dup_policy = DuplicatePolicy(on_duplicate)
    if "tasks" in data:
        seen: Dict[str, ATIFTask] = {}
        for t_dict in data.get("tasks", []):
            try:
                task = parse_task_dict(t_dict)
            except SuiteValidationError:
                if strict:
                    raise
                continue
            if task.task_id in seen:
                if dup_policy == DuplicatePolicy.RAISE:
                    raise DuplicateTaskError(task.task_id)
                elif dup_policy == DuplicatePolicy.OVERWRITE:
                    seen[task.task_id] = task
                elif dup_policy == DuplicatePolicy.IGNORE:
                    continue
            else:
                seen[task.task_id] = task

        return BenchmarkSuite(
            name=name or data.get("name", "in-memory-suite"),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            tasks=list(seen.values()),
            metadata=data.get("metadata", {}),
        )
    else:
        task = parse_task_dict(data)
        return BenchmarkSuite(
            name=name or "single-task-suite",
            tasks=[task],
        )


def load_suite_from_list(
    data: Sequence[Dict[str, Any]],
    name: Optional[str] = None,
    on_duplicate: Union[str, DuplicatePolicy] = DuplicatePolicy.RAISE,
    strict: bool = True,
) -> BenchmarkSuite:
    """Ingest a suite from a list of task dictionaries."""
    dup_policy = DuplicatePolicy(on_duplicate)
    seen: Dict[str, ATIFTask] = {}
    for item in data:
        try:
            task = parse_task_dict(item)
        except SuiteValidationError:
            if strict:
                raise
            continue
        if task.task_id in seen:
            if dup_policy == DuplicatePolicy.RAISE:
                raise DuplicateTaskError(task.task_id)
            elif dup_policy == DuplicatePolicy.OVERWRITE:
                seen[task.task_id] = task
            elif dup_policy == DuplicatePolicy.IGNORE:
                continue
        else:
            seen[task.task_id] = task

    return BenchmarkSuite(
        name=name or "task-list-suite",
        tasks=list(seen.values()),
    )


def load_suite_from_json_string(
    json_str: str,
    name: Optional[str] = None,
    on_duplicate: Union[str, DuplicatePolicy] = DuplicatePolicy.RAISE,
    strict: bool = True,
) -> BenchmarkSuite:
    """Ingest a suite from a JSON string."""
    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as err:
        raise SuiteLoadError(f"Malformed JSON string: {err}", cause=err) from err

    if isinstance(parsed, dict):
        return load_suite_from_dict(parsed, name=name, on_duplicate=on_duplicate, strict=strict)
    elif isinstance(parsed, list):
        return load_suite_from_list(parsed, name=name, on_duplicate=on_duplicate, strict=strict)
    raise SuiteLoadError(f"JSON string root must be dict or list, got {type(parsed).__name__}")


def load_suite_from_yaml_string(
    yaml_str: str,
    name: Optional[str] = None,
    on_duplicate: Union[str, DuplicatePolicy] = DuplicatePolicy.RAISE,
    strict: bool = True,
) -> BenchmarkSuite:
    """Ingest a suite from a YAML string (supports multi-document YAML)."""
    try:
        docs = list(yaml.safe_load_all(yaml_str))
    except yaml.YAMLError as err:
        raise SuiteLoadError(f"Malformed YAML string: {err}", cause=err) from err

    valid_docs = [d for d in docs if d is not None]
    if not valid_docs:
        return BenchmarkSuite(name=name or "empty-suite", tasks=[])

    if len(valid_docs) == 1 and isinstance(valid_docs[0], dict) and "tasks" in valid_docs[0]:
        return load_suite_from_dict(valid_docs[0], name=name, on_duplicate=on_duplicate, strict=strict)

    all_task_dicts: List[Dict[str, Any]] = []
    for d in valid_docs:
        if isinstance(d, list):
            all_task_dicts.extend(d)
        elif isinstance(d, dict):
            all_task_dicts.append(d)

    return load_suite_from_list(all_task_dicts, name=name, on_duplicate=on_duplicate, strict=strict)


# -----------------------------------------------------------------------------
# Serialization Helpers
# -----------------------------------------------------------------------------

def suite_to_dict(suite: BenchmarkSuite) -> Dict[str, Any]:
    """Serialize a BenchmarkSuite into a canonical JSON-compatible dictionary."""
    return suite.model_dump(mode="json")


def suite_to_json(suite: BenchmarkSuite, indent: int = 2) -> str:
    """Serialize a BenchmarkSuite into a formatted JSON string."""
    return json.dumps(suite_to_dict(suite), indent=indent)


def suite_to_yaml(suite: BenchmarkSuite) -> str:
    """Serialize a BenchmarkSuite into a formatted YAML string."""
    return yaml.safe_dump(suite_to_dict(suite), sort_keys=False)


def save_suite_to_file(
    suite: BenchmarkSuite,
    file_path: Union[str, Path],
    format: Optional[str] = None,
    indent: int = 2,
) -> Path:
    """Save a BenchmarkSuite to disk in JSON or YAML format, auto-creating directories."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fmt = format.lower().strip() if format else path.suffix.lower().lstrip(".")
    if fmt in ("yaml", "yml"):
        content = suite_to_yaml(suite)
    else:
        content = suite_to_json(suite, indent=indent)

    path.write_text(content, encoding="utf-8")
    return path


save_suite = save_suite_to_file
load_benchmark_suite = load_suite


class BenchmarkLoader:
    """Compatibility loader namespace for test suites."""
    load = staticmethod(load_suite)
