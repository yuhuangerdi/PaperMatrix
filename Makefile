CONDA_ENV ?= Paper

.PHONY: verify backend-check frontend-check dev-backend dev-frontend

verify: backend-check frontend-check
	conda run -n $(CONDA_ENV) python scripts/validate_specs.py

backend-check:
	conda run -n $(CONDA_ENV) python -m pytest
	conda run -n $(CONDA_ENV) python -m ruff check backend scripts/create_example_workspace.py
	conda run -n $(CONDA_ENV) python -m ruff format --check backend scripts/create_example_workspace.py
	conda run -n $(CONDA_ENV) python -m mypy backend/src

frontend-check:
	npm --prefix frontend run lint
	npm --prefix frontend run typecheck
	npm --prefix frontend run test -- --run
	npm --prefix frontend run build
	npm --prefix frontend run format:check

dev-backend:
	conda run -n $(CONDA_ENV) uvicorn papermatrix.main:app --host 127.0.0.1 --port 8000 --reload

dev-frontend:
	npm --prefix frontend run dev
