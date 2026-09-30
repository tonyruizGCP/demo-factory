export UV_EXTRA_INDEX_URL ?= https://oauth2accesstoken:$(shell gcloud auth print-access-token 2>/dev/null)@us-python.pkg.dev/artifact-foundry-prod/ah-3p-staging-python/simple/
export UV_INDEX_STRATEGY ?= unsafe-best-match
export UV_DEFAULT_INDEX ?= https://pypi.org/simple

.PHONY: setup run test eval deploy ge-info clean

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

run:
	fuser -k 8080/tcp 2>/dev/null || true
	python3 -m app.main

test:
	pytest tests/ -v

eval:
	python3 -m app.eval_runner --min-score 0.85

deploy:
	./scripts/deploy_cloudrun.sh

ge-info:
	./scripts/ge_info.sh

clean:
	rm -rf .pytest_cache __pycache__ app/__pycache__ tests/__pycache__ .gcs_local_mirror
