from datetime import datetime
from pathlib import Path

from cosmos import DbtDag, ExecutionConfig, LoadMode, ProfileConfig, ProjectConfig, RenderConfig

DBT_DIR = Path(__file__).parents[2] / "dbt"

# One task per model (+ its tests), read from manifest.json: no dbt call at DAG parse time.
thelook_dbt = DbtDag(
    dag_id="thelook_dbt",
    project_config=ProjectConfig(
        dbt_project_path=DBT_DIR,
        manifest_path=DBT_DIR / "target" / "manifest.json",
    ),
    render_config=RenderConfig(load_method=LoadMode.DBT_MANIFEST),
    profile_config=ProfileConfig(
        profile_name="thelook",
        target_name="dev",
        profiles_yml_filepath=DBT_DIR / "profiles.yml",
    ),
    execution_config=ExecutionConfig(dbt_executable_path="/home/airflow/dbt-venv/bin/dbt"),
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["analytics", "dbt"],
)
