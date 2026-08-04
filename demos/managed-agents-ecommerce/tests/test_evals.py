import pytest
from eval_runner import run_eval_suite

def test_eval_suite_execution():
    status = run_eval_suite()
    assert status == 0, "Evaluation suite must pass with score >= 0.85"
