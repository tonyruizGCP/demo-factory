.PHONY: setup run test eval register-oauth clean

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

run:
	PYTHONPATH=. python3 -m app.main

test:
	PYTHONPATH=. pytest tests/

eval:
	PYTHONPATH=. python3 -m app.eval_runner

register-oauth:
	PYTHONPATH=. python3 tools/register_oauth.py

clean:
	rm -rf .pytest_cache __pycache__ app/__pycache__ tests/__pycache__ .venv
