"""Synthetic benchmark tasks tailored for Gemini Enterprise Coding Harness."""
from __future__ import annotations

from typing import List
from harness_optimizer.benchhub.schema import (
    ATIFTask,
    BehavioralTag,
    BenchmarkSuite,
    DifficultyLevel,
    VerificationSpec,
)


def get_enterprise_coding_tasks() -> List[ATIFTask]:
    """Returns standard curated coding tasks evaluating Gemini Enterprise Coding Harness capabilities."""
    return [
        ATIFTask(
            task_id="ge_task_01_async_refactor",
            instruction="Refactor SessionManager session state handling to support asynchronous lock acquisitions.",
            difficulty=DifficultyLevel.HARD,
            behavioral_tags=[BehavioralTag.TOOL_SELECTION, BehavioralTag.STATE_MUTATION],
            verification=VerificationSpec(
                command="pytest tests/unit/test_session_manager.py -k async_refactor",
                timeout_seconds=30,
            ),
            metadata={"domain": "concurrency", "subsystem": "session_manager"},
        ),
        ATIFTask(
            task_id="ge_task_02_lsp_symbol_lookup",
            instruction="Locate definition and cross-references of MemoryBankService to verify callers before modifying interface.",
            difficulty=DifficultyLevel.MEDIUM,
            behavioral_tags=[BehavioralTag.TOOL_SELECTION, BehavioralTag.MULTI_STEP_RETRIEVAL],
            verification=VerificationSpec(
                command="python3 -c 'from app.tools.lsp_tools import lsp_find_definition; assert lsp_find_definition(\"MemoryBankService\") is not None'",
                timeout_seconds=15,
            ),
            metadata={"domain": "lsp_navigation", "subsystem": "memory_bank"},
        ),
        ATIFTask(
            task_id="ge_task_03_prewalk_guideline_grounding",
            instruction="Query Vertex AI Memory Bank during prewalk grounding to ensure enterprise logging compliance rules are retrieved.",
            difficulty=DifficultyLevel.EASY,
            behavioral_tags=[BehavioralTag.CONSTRAINT_ADHERENCE, BehavioralTag.MULTI_STEP_RETRIEVAL],
            verification=VerificationSpec(
                command="python3 -c 'from app.services.memory_bank import MemoryBankService; assert len(MemoryBankService().list_all()) > 0'",
                timeout_seconds=15,
            ),
            metadata={"domain": "grounding", "subsystem": "memory_bank"},
        ),
        ATIFTask(
            task_id="ge_task_04_semantic_patch_ast_guard",
            instruction="Apply semantic patch to app/config.py while preserving AST syntax validity and preventing corrupt syntax diffs.",
            difficulty=DifficultyLevel.MEDIUM,
            behavioral_tags=[BehavioralTag.STATE_MUTATION, BehavioralTag.CONSTRAINT_ADHERENCE],
            verification=VerificationSpec(
                command="python3 -m py_compile app/config.py",
                timeout_seconds=15,
            ),
            metadata={"domain": "ast_patching", "subsystem": "config"},
        ),
        ATIFTask(
            task_id="ge_task_05_worktree_isolation",
            instruction="Delegate risky refactor to subagent in an isolated Git worktree without dirtying the active branch.",
            difficulty=DifficultyLevel.HARD,
            behavioral_tags=[BehavioralTag.STATE_MUTATION, BehavioralTag.TOOL_SELECTION],
            verification=VerificationSpec(
                command="git status --porcelain",
                timeout_seconds=20,
            ),
            metadata={"domain": "git_isolation", "subsystem": "worktree"},
        ),
        ATIFTask(
            task_id="ge_task_06_dap_test_runner",
            instruction="Execute DAP test runner to verify test suite passes after applying bugfix in services/workspace_context.py.",
            difficulty=DifficultyLevel.EASY,
            behavioral_tags=[BehavioralTag.TOOL_SELECTION, BehavioralTag.CONSTRAINT_ADHERENCE],
            verification=VerificationSpec(
                command="pytest tests/unit/ -q",
                timeout_seconds=30,
            ),
            metadata={"domain": "debugging", "subsystem": "dap_runner"},
        ),
        ATIFTask(
            task_id="ge_task_07_memory_consolidation",
            instruction="Synthesize learned workspace rule into Memory Bank after discovering new repo naming conventions.",
            difficulty=DifficultyLevel.MEDIUM,
            behavioral_tags=[BehavioralTag.CONSTRAINT_ADHERENCE, BehavioralTag.STATE_MUTATION],
            verification=VerificationSpec(
                command="python3 -c 'from app.services.memory_bank import MemoryBankService; mb = MemoryBankService(); mb.create_memory(\"New Rule\"); assert len(mb.list_all()) > 0'",
                timeout_seconds=15,
            ),
            metadata={"domain": "consolidation", "subsystem": "memory_bank"},
        ),
        ATIFTask(
            task_id="ge_task_08_multi_turn_session_rewind",
            instruction="Perform 3-turn interactive refinement in SessionManager and test rewind rollback mechanism.",
            difficulty=DifficultyLevel.EXPERT,
            behavioral_tags=[BehavioralTag.MULTI_STEP_RETRIEVAL, BehavioralTag.STATE_MUTATION],
            verification=VerificationSpec(
                command="python3 -c 'from app.services.session_manager import SessionManager; sm = SessionManager(); s = sm.get_or_create(\"rw\"); s.add_turn(\"user\", \"hi\"); assert len(s.turns) == 1'",
                timeout_seconds=20,
            ),
            metadata={"domain": "session_tree", "subsystem": "session_manager"},
        ),
    ]


def generate_enterprise_benchmark_suite(
    suite_id: str = "gemini_enterprise_eval_suite",
    num_tasks: int = 10,
) -> BenchmarkSuite:
    """Generates a BenchmarkSuite composed of enterprise coding tasks."""
    base_tasks = get_enterprise_coding_tasks()
    tasks: List[ATIFTask] = []
    
    # Repeat and parameterize to reach requested num_tasks
    while len(tasks) < num_tasks:
        idx = len(tasks)
        base = base_tasks[idx % len(base_tasks)]
        new_task = ATIFTask(
            task_id=f"{base.task_id}_{idx:02d}",
            instruction=f"[Trial {idx:02d}] {base.instruction}",
            difficulty=base.difficulty,
            behavioral_tags=list(base.behavioral_tags),
            verification=base.verification,
            metadata=dict(base.metadata or {}),
        )
        tasks.append(new_task)

    return BenchmarkSuite(
        suite_id=suite_id,
        tasks=tasks[:num_tasks],
        metadata={"target_harness": "gemini-enterprise-coding-harness"},
    )
