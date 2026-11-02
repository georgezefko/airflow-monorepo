-include .env
export
export GOOGLE_APPLICATION_CREDENTIALS ?= $(GCP_KEYFILE)

DBT = uv run dbt --no-use-colors
DBT_ARGS = --project-dir dbt --profiles-dir dbt

.PHONY: setup up down logs test lint dbt-debug dbt-parse dbt-build dbt-compile gantt

setup:            ## local venv + git hooks
	uv sync
	uv run pre-commit install

up: dbt-parse     ## Airflow on http://localhost:8080 (Cosmos reads dbt/target/manifest.json)
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f airflow

test:             ## DAG integrity, inside the real Airflow image (needs `make up`)
	docker compose exec airflow python -m pytest tests -q

lint:
	uv run pre-commit run --all-files

dbt-debug:
	$(DBT) debug $(DBT_ARGS)

dbt-parse:
	$(DBT) parse $(DBT_ARGS)

dbt-compile:
	$(DBT) compile $(DBT_ARGS)

dbt-build:        ## e.g. make dbt-build s=fct_events
	$(DBT) build $(DBT_ARGS) $(if $(s),-s $(s))

gantt:            ## demo 5: timeline of the last run
	uv run python scripts/gantt.py
