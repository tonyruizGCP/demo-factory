.PHONY: setup run test eval clean kill-port

PYTHON ?= python3
PORT ?= 8080

setup:
	$(PYTHON) -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

kill-port:
	fuser -k $(PORT)/tcp || true

run: kill-port
	$(PYTHON) -m app.main

test:
	pytest tests/

eval:
	$(PYTHON) -m app.eval_runner

clean:
	rm -rf .venv __pycache__ .pytest_cache generated_projects/
