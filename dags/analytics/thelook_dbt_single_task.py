from datetime import datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

# Demo 6 "before": the whole project is one opaque task. One failure = rerun everything.
with DAG(
    dag_id="thelook_dbt_single_task",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["analytics", "dbt"],
):
    BashOperator(
        task_id="dbt_build",
        bash_command=(
            "/home/airflow/dbt-venv/bin/dbt build"
            " --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt"
            " --target-path /tmp/dbt-target --log-path /tmp/dbt-logs"
        ),
    )
