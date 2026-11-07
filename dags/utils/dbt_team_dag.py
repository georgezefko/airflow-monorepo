from datetime import datetime

from cosmos import DbtDag, ExecutionConfig, LoadMode, ProfileConfig, ProjectConfig, RenderConfig

DBT_PROJECT = "/opt/airflow/analytics"


def team_dag(team, schedule):
    return DbtDag(
        dag_id=f"{team}_dbt",
        project_config=ProjectConfig(
            DBT_PROJECT,
            manifest_path=f"{DBT_PROJECT}/target/manifest.json",
        ),
        render_config=RenderConfig(
            load_method=LoadMode.DBT_MANIFEST,
            select=[f"tag:{team}"],
        ),
        profile_config=ProfileConfig(
            profile_name="analytics",
            target_name="dev",
             profiles_yml_filepath=f"{DBT_PROJECT}/profiles.yml",
        ),
        execution_config=ExecutionConfig(
            dbt_executable_path="/home/airflow/dbt-venv/bin/dbt",
        ),
        schedule=schedule,
        start_date=datetime(2026, 1, 1),
        catchup=False,
        tags=[team, "dbt"],
    )