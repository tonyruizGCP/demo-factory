"""Formal Empirical Stress Test Suite for Challenger 1 Verification."""

import os
import threading
import time
import concurrent.futures
import psutil
import pytest

from harness_optimizer.harbor.config import SandboxConfig
from harness_optimizer.harbor.executor import ConcurrentBatchExecutor
from harness_optimizer.harbor.sandbox import InMemoryMockHarness, SubprocessSandbox, AgentCandidate
from harness_optimizer.lifecycle.state_machine import (
    OptimizationStateMachine,
    OptimizationState,
    ALLOWED_TRANSITIONS,
    InvalidStateTransitionError,
)


def test_concurrency_stress_100_trials_16_threads_determinism():
    """Execute 100 trials concurrently across 16 threads in ConcurrentBatchExecutor with InMemoryMockHarness.

    Verify deterministic results across identical seeds and zero race conditions.
    """
    num_trials = 100
    num_threads = 16
    tasks = [{"task_id": f"stress_task_{i:04d}", "metadata": {"idx": i}} for i in range(num_trials)]
    candidate = AgentCandidate(candidate_id="stress_cand_v1")

    # Run multiple batches with identical seed 42
    runs = []
    for _ in range(4):
        harness = InMemoryMockHarness(failure_rate=0.4, seed=42)
        executor = ConcurrentBatchExecutor(sandbox=harness, max_workers=num_threads)
        results = executor.execute_batch(tasks, candidate)
        runs.append(results)

    # Verify length and ordering preservation
    for run in runs:
        assert len(run) == num_trials
        for i, res in enumerate(run):
            assert res.task_id == f"stress_task_{i:04d}"

    # Verify identical deterministic results bit-for-bit across all runs
    base_run = runs[0]
    for other_run in runs[1:]:
        for i in range(num_trials):
            assert base_run[i].passed == other_run[i].passed
            assert base_run[i].exit_code == other_run[i].exit_code
            assert base_run[i].raw_error_message == other_run[i].raw_error_message


def test_watchdog_timeout_clean_termination_and_zero_zombies():
    """Run SubprocessSandbox against hanging commands (sleep 10) with sub-second timeouts (0.2s).

    Verify clean process termination and zero leaked zombie processes.
    """
    timeout_sec = 0.2
    config = SandboxConfig(timeout_sec=timeout_sec, cleanup=True)
    sandbox = SubprocessSandbox(config=config)
    candidate = AgentCandidate(candidate_id="watchdog_cand")

    current_pid = os.getpid()
    parent_proc = psutil.Process(current_pid)

    def count_sleep_10():
        count = 0
        for p in psutil.process_iter(["cmdline", "pid"]):
            try:
                cmd = " ".join(p.info["cmdline"] or [])
                if "sleep" in cmd and "10" in cmd and p.info["pid"] != current_pid:
                    count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return count

    initial_sleep_count = count_sleep_10()

    task = {
        "task_id": "watchdog_hang_task",
        "verification": {
            "command": "sleep 10",
            "timeout_sec": timeout_sec,
        },
    }

    # Execute 5 repeated timeout trials
    for _ in range(5):
        t0 = time.perf_counter()
        res = sandbox.execute_trial(task, candidate)
        elapsed = time.perf_counter() - t0

        assert 0.19 <= elapsed < 1.0
        assert not res.passed
        assert res.exit_code == -9
        assert "watchdog timed out" in (res.raw_error_message or "")

    # Let OS reap any finishing process
    time.sleep(0.3)

    # Verify no leaked sleep 10 processes
    final_sleep_count = count_sleep_10()
    assert final_sleep_count == initial_sleep_count, (
        f"Leaked sleep 10 processes: started with {initial_sleep_count}, now {final_sleep_count}"
    )

    # Verify no zombie processes under our process tree
    zombies = [c for c in parent_proc.children(recursive=True) if c.status() == psutil.STATUS_ZOMBIE]
    assert len(zombies) == 0, f"Found leaked zombie processes: {zombies}"


def test_state_machine_exhaustive_and_concurrent_illegal_transitions():
    """Trigger concurrent transitions and verify that all illegal state transitions strictly raise InvalidStateTransitionError."""
    all_states = list(OptimizationState)

    # 1. Exhaustive 7x7 matrix validation
    for s_from in all_states:
        for s_to in all_states:
            sm = OptimizationStateMachine(initial_state=s_from)
            is_allowed = s_to in ALLOWED_TRANSITIONS[s_from]
            if is_allowed:
                sm.transition(s_to)
                assert sm.current_state == s_to
            else:
                with pytest.raises(InvalidStateTransitionError):
                    sm.transition(s_to)

    # 2. Concurrent transitions race condition stress test
    sm_concurrent = OptimizationStateMachine(initial_state=OptimizationState.IDLE)
    num_threads = 16
    attempts_per_thread = 50
    barrier = threading.Barrier(num_threads)

    legal_count = 0
    illegal_count = 0
    lock = threading.Lock()

    def worker(tid):
        nonlocal legal_count, illegal_count
        barrier.wait()
        for step in range(attempts_per_thread):
            target = all_states[(tid + step) % len(all_states)]
            try:
                sm_concurrent.transition(target)
                with lock:
                    legal_count += 1
            except InvalidStateTransitionError:
                with lock:
                    illegal_count += 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as pool:
        futures = [pool.submit(worker, i) for i in range(num_threads)]
        for f in concurrent.futures.as_completed(futures):
            f.result()

    assert legal_count + illegal_count == num_threads * attempts_per_thread
    assert len(sm_concurrent.state_history) == legal_count

    # Check history invariants
    for idx, (f_state, t_state) in enumerate(sm_concurrent.state_history):
        assert t_state in ALLOWED_TRANSITIONS[f_state]
        if idx > 0:
            assert f_state == sm_concurrent.state_history[idx - 1][1]
