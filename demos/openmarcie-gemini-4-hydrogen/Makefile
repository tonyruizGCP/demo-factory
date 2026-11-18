.PHONY: test eval run download

download:
	uv run python download_subset.py

test:
	DEMO_SIMULATION=1 uv run python -m pytest tests/

eval:
	DEMO_SIMULATION=1 uv run python -m app.eval_runner

run:
	uv run uvicorn app.main:web_app --host 0.0.0.0 --port $${PORT:-8080}
