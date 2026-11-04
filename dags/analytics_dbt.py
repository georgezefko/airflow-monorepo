from datetime import datetime

from cosmos import DbtDag, ExecutionConfig, ProfileConfig, ProjectConfig

analytics_dbt = DbtDag(
    dag_id="analytics_dbt",
    project_config=ProjectConfig("/opt/airflow/analytics"),
    profile_config=ProfileConfig(
        profile_name="analytics",
        target_name="dev",
        profiles_yml_filepath="/home/airflow/.dbt/profiles.yml",
    ),
    execution_config=ExecutionConfig(
        dbt_executable_path="/home/airflow/dbt-venv/bin/dbt",
    ),
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
)