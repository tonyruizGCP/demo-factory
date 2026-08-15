.PHONY: test eval run serve compare clean

test:
	pytest tests/ -v

eval:
	python3 cli.py run-eval --scenario simbian-apt29-01 --harness antigravity

eval-live:
	python3 cli.py run-eval --scenario simbian-apt29-01 --harness antigravity --live

compare:
	python3 cli.py compare-harnesses --scenario simbian-apt29-01

serve:
	python3 cli.py serve --host 0.0.0.0 --port 8080

skills:
	python3 cli.py list-skills

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
