.PHONY: setup run test eval clean

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

run:
	python3 app.py

test:
	pytest tests/

eval:
	python3 eval_runner.py

clean:
	rm -rf .venv __pycache__ .pytest_cache
