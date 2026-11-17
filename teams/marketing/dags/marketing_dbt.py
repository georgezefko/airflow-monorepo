# Airflow DAG for the marketing team
import sys
from pathlib import Path

from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.sdk import Asset

# Platform's DAG helpers, from this bundle's own checkout (pinned by this team's tag)
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "teams" / "platform" / "lib"))
from dbt_team_dag import team_dag  # noqa: E402

STAGING_READY = Asset("analytics_staging_ready")
MARKETING_READY = Asset("analytics_marketing_ready")

marketing_dbt = team_dag("marketing", schedule=STAGING_READY)

with marketing_dbt:
    marketing_dbt.leaves >> EmptyOperator(task_id="marketing_ready", outlets=[MARKETING_READY])
