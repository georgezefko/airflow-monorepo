# Weekly revenue from BigQuery to Postgres, after sales' dbt models are built:
# platform's common extract and load apps, with sales' SQL and sales' own transform in between.
import sys
from datetime import datetime
from pathlib import Path

from airflow.sdk import DAG, Asset

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "teams" / "platform" / "lib"))
from app_task import DATA, app_task  # noqa: E402

SALES = Path(__file__).resolve().parents[1]
SQL = SALES / "sql"

with DAG(
    "sales_to_postgres",
    schedule=Asset("analytics_sales_ready"),
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["sales", "app", "v" + (SALES / "version.txt").read_text().strip()],
):
    extract = app_task(
        "platform/common/bq-extract", "extract",
        ["--sql", (SQL / "weekly_revenue.sql").read_text(), "--out", f"{DATA}/extract.parquet"],
    )
    transform = app_task(
        "sales/transform", "transform",
        ["--in", f"{DATA}/extract.parquet", "--out", f"{DATA}/transform.parquet"],
    )
    load = app_task(
        "platform/common/pg-load", "load",
        ["--in", f"{DATA}/transform.parquet", "--table", "sales.weekly_revenue",
         "--ddl", (SQL / "weekly_revenue_postgres.sql").read_text()],
        postgres=True,
    )
    extract >> transform >> load
