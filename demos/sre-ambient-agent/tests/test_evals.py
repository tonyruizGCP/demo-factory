import pytest
from app.eval_runner import run_sre_eval_suite

def test_eval_suite():
    ret = run_sre_eval_suite()
    assert ret == 0
