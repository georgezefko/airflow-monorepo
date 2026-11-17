# Airflow DAG for the sales team
import sys
from pathlib import Path

from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.sdk import Asset

# Platform's DAG helpers, from this bundle's own checkout (pinned by this team's tag)
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "teams" / "platform" / "lib"))
from dbt_team_dag import team_dag  # noqa: E402

STAGING_READY = Asset("analytics_staging_ready")
SALES_READY = Asset("analytics_sales_ready")

sales_dbt = team_dag("sales", schedule=STAGING_READY)

with sales_dbt:
    sales_dbt.leaves >> EmptyOperator(task_id="sales_ready", outlets=[SALES_READY])
