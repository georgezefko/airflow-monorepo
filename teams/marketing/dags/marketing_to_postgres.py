# Orders per traffic source from BigQuery to Postgres, after marketing's dbt models are built:
# platform's common extract and load apps, with marketing's SQL and marketing's own transform in between.
import sys
from datetime import datetime
from pathlib import Path

from airflow.sdk import DAG, Asset

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "teams" / "platform" / "lib"))
from app_task import DATA, app_task  # noqa: E402

MARKETING = Path(__file__).resolve().parents[1]
SQL = MARKETING / "sql"

with DAG(
    "marketing_to_postgres",
    schedule=Asset("analytics_marketing_ready"),
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["marketing", "app", "v" + (MARKETING / "version.txt").read_text().strip()],
):
    extract = app_task(
        "platform/common/bq-extract", "extract",
        ["--sql", (SQL / "traffic_sources.sql").read_text(), "--out", f"{DATA}/extract.parquet"],
    )
    transform = app_task(
        "marketing/transform", "transform",
        ["--in", f"{DATA}/extract.parquet", "--out", f"{DATA}/transform.parquet"],
    )
    load = app_task(
        "platform/common/pg-load", "load",
        ["--in", f"{DATA}/transform.parquet", "--table", "marketing.traffic_sources",
         "--ddl", (SQL / "traffic_sources_postgres.sql").read_text()],
        postgres=True,
    )
    extract >> transform >> load
