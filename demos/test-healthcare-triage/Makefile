.PHONY: setup run test eval clean

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

run:
	python3 -m app.main

test:
	pytest tests/

eval:
	python3 -m app.eval_runner
