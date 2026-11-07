# Airflow DAG for the marketing team
from airflow.sdk import Asset
from utils.dbt_team_dag import team_dag

STAGING_READY = Asset("analytics_staging_ready")
marketing_dbt = team_dag("marketing", schedule=STAGING_READY)