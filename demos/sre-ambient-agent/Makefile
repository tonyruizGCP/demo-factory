.PHONY: setup run test eval seed clean

PYTHON ?= python3

setup:
	$(PYTHON) -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

run:
	$(PYTHON) -m app.main

seed:
	$(PYTHON) -m app.setup_bigquery_mock_data --dry-run

test:
	pytest tests/

eval:
	$(PYTHON) -m app.eval_runner

clean:
	rm -rf .venv __pycache__ .pytest_cache mock_sre_logs.json
