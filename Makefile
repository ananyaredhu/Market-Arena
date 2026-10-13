.PHONY: setup api test lint schemas fixtures web

PY = .venv/bin/python

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	cd frontend && npm install

api:
	MOCK=1 LLM_MODE=mock $(PY) -m uvicorn backend.main:app --reload --port 8000

web:
	cd frontend && npm run dev

test:
	$(PY) -m pytest

lint:
	.venv/bin/ruff check backend contracts scripts

# Regenerate contracts/*.schema.json from the Pydantic models
schemas:
	$(PY) -m scripts.export_schemas

# Regenerate the generated fixtures (population, run_result)
fixtures:
	$(PY) -m scripts.make_fixtures
