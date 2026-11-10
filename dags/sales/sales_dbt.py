# Airflow DAG for the sales team
from airflow.sdk import Asset
from utils.dbt_team_dag import team_dag

STAGING_READY = Asset("analytics_staging_ready")
sales_dbt = team_dag("sales", schedule=STAGING_READY)
