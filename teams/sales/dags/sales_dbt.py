# Airflow DAG for the sales team
import sys
from pathlib import Path

from airflow.sdk import Asset

# Platform's DAG helpers, from this bundle's own checkout (pinned by this team's tag)
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "teams" / "platform" / "lib"))
from dbt_team_dag import team_dag  # noqa: E402

STAGING_READY = Asset("analytics_staging_ready")
sales_dbt = team_dag("sales", schedule=STAGING_READY)
