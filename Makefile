-include .env
export
DBT = docker compose exec -T -w /opt/airflow/repo airflow-worker /home/airflow/dbt-venv/bin/dbt
AIRFLOW = docker compose exec -T airflow-scheduler airflow
DAGS ?= platform_dbt sales_dbt marketing_dbt
TRIGGER ?= platform_dbt

.DEFAULT_GOAL := help
.PHONY: help all up down parse test run dbt-debug dbt-build gantt

help:  ## Show the available commands
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed -E 's/:.*## /: /'

all: up test run  ## Start Airflow, run the tests, and trigger the DAGs

up: parse  ## Refresh the manifest, build the image, and start Airflow
	docker compose up -d --build --wait

down:  ## Stop Airflow and keep its metadata
	docker compose down

parse:  ## Regenerate target/manifest.json
	uv run dbt parse

test:  ## Run the DAG tests (needs make up)
	docker compose exec -T -w /opt/airflow/repo airflow-worker python -m pytest tests -q -p no:cacheprovider

# ponytail: triggers without waiting for the result, watch the run in the UI
run:  ## Unpause the DAGs and trigger one (needs make up), e.g. make run TRIGGER=sales_dbt
	$(AIRFLOW) dags reserialize
	@for dag in $(DAGS); do \
	        $(AIRFLOW) dags unpause $$dag || exit 1; \
	done
	$(AIRFLOW) dags trigger $(TRIGGER)

dbt-debug:  ## Check the BigQuery connection from the container (needs make up)
	$(DBT) debug

dbt-build:  ## Run dbt build in the container (needs make up), e.g. make dbt-build s=tag:sales
	$(DBT) build $(if $(s),--select $(s))

gantt:  ## Draw the last dbt run as a timeline
	python3 scripts/gantt.py