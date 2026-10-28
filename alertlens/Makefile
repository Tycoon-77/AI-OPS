VENV=.venv
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

.PHONY: setup data pipeline api ui test demo lint

setup:
	python3.11 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

data:
	$(PYTHON) -m alertlens.simulator.generate --seed 42

pipeline:
	$(PYTHON) -m alertlens.pipeline run --all

api:
	$(VENV)/bin/uvicorn alertlens.api.main:app --port 8000 --reload --app-dir src

ui:
	$(VENV)/bin/streamlit run dashboard/app.py

test:
	$(VENV)/bin/pytest -q --tb=short

lint:
	$(VENV)/bin/ruff check src/ tests/
	$(VENV)/bin/ruff format --check src/ tests/

demo:
	$(PYTHON) -m alertlens.pipeline run --all
