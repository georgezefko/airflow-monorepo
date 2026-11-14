from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.sdk import Asset
from dbt_team_dag import team_dag

STAGING_READY = Asset("analytics_staging_ready")

platform_dbt = team_dag("platform", schedule="@daily")

with platform_dbt:
    platform_dbt.leaves >> EmptyOperator(task_id="staging_ready", outlets=[STAGING_READY])