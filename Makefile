# Omytea Personal Future Console — common dev / ops targets.
#
# Quick reference:
#     make help            list targets
#     make install         create venv + install deps
#     make test            run the full mock-mode test suite
#     make eval            run the pipeline-invariant eval harness
#     make real-e2e        run a real Ollama-backed E2E (slow on CPU)
#     make bundle          build the one-folder PyInstaller bundle
#     make bundle-onefile  build the single-binary PyInstaller bundle
#     make docker          build the Docker image
#     make run             launch streamlit run app.py
#     make snapshot        dump SQLite predictions to JSON
#     make clean           remove venv + build artefacts

.PHONY: help install test eval real-e2e bundle bundle-onefile docker run snapshot clean release-tarball

PY ?= python3
VENV ?= .venv

help:
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Create venv + install Python deps (one-shot setup)
	bash scripts/install.sh

test: ## Run the full mock-mode test suite (no LLM, no network)
	OMYTEA_CONSOLE_MOCK=1 $(VENV)/bin/python -m pytest -q

eval: ## Run the pipeline-invariant eval harness
	OMYTEA_CONSOLE_MOCK=1 $(VENV)/bin/python -m eval.run_eval

real-e2e: ## Run real Ollama-backed E2E (slow on CPU; needs ollama pull llava:7b)
	$(VENV)/bin/python -u scripts/real_e2e.py

bundle: ## Build the one-folder PyInstaller native bundle
	bash scripts/build_native.sh --folder

bundle-onefile: ## Build the single-binary PyInstaller bundle
	bash scripts/build_native.sh --onefile

docker: ## Build the Docker image
	docker build -t omytea-console:$$($(VENV)/bin/python -c 'import _brand; print(_brand.BRAND_VERSION)') .

run: ## Launch streamlit run app.py
	$(VENV)/bin/streamlit run app.py

snapshot: ## Dump the SQLite predictions DB to JSON
	$(VENV)/bin/python scripts/snapshot_predictions.py --pretty

release-tarball: bundle ## Build + tar.gz the bundle for release upload
	cd dist && tar czf "omytea-console-$$(uname -s)-$$(uname -m).tar.gz" omytea-console/
	@ls -lh dist/omytea-console-*.tar.gz

clean: ## Remove venv, build/, dist/, __pycache__, .pytest_cache
	rm -rf $(VENV) build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
