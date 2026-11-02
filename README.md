# airflow-monorepo

Multi-team Airflow: DAGs, Docker apps and dbt in one repo. Phase 1: a dbt project on
`bigquery-public-data.thelook_ecommerce`, rendered into Airflow tasks with Cosmos.

```
dags/analytics/      Cosmos DAG for the dbt project
dbt/                 staging -> intermediate -> marts (fct_events is the incremental experiment)
docker/airflow/      Airflow 3 image, Cosmos + dbt in its own venv (LOCAL execution mode)
tests/dags/          DAG integrity test
```

## Local setup

Needs Docker, [uv](https://docs.astral.sh/uv/) and a GCP service account key with
BigQuery Job User + Data Editor on your project.

```bash
cp .env.example .env   # fill in project, key path, your dataset
make setup             # .venv with dbt, ruff, sqlfluff + pre-commit hooks
make dbt-debug         # check the BigQuery connection
make dbt-build         # build everything from your laptop
make up                # Airflow on http://localhost:8080 (no login locally)
make test              # DAG integrity test inside the running Airflow container
```

Output tables land in `$DBT_DATASET` (location US, same as thelook).

## Post 1 runbook

The demos for "what dbt actually does when you type `dbt run`" are in
[docs/post-1-dbt-internals.md](docs/post-1-dbt-internals.md).
