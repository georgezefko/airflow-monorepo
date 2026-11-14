import sys
from datetime import datetime
from pathlib import Path

from cosmos import DbtDag, ExecutionConfig, LoadMode, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import InvocationMode

DBT = "/home/airflow/dbt-venv/bin/dbt"


def team_dag(team, schedule):
    """One DAG per team, running the dbt models in teams/<team>/dbt/.

    The dbt project is the checkout the calling DAG file came from: teams/<team>/dags/<file>.py
    is three folders below the repository root. In a git bundle that's the team's version
    (e.g. sales-v1.0.1), so DAGs and models always come from the same commit.
    """
    # ponytail: reads the caller's file, so team DAG files stay one line; pass the path explicitly if
    # a DAG file ever lives deeper than teams/<team>/dags/
    project = Path(sys._getframe(1).f_globals["__file__"]).resolve().parents[3]

    return DbtDag(
        dag_id=f"{team}_dbt",
        project_config=ProjectConfig(
            project,
            models_relative_paths=[f"teams/{team}/dbt"],  # Cosmos otherwise expects models/ at the root
        ),
        render_config=RenderConfig(
            load_method=LoadMode.DBT_LS,  # list models from the checkout; Cosmos caches it per version
            select=[f"path:teams/{team}/dbt"],
            dbt_executable_path=DBT,
            invocation_mode=InvocationMode.SUBPROCESS,  # dbt is in its own venv, not importable
        ),
        profile_config=ProfileConfig(
            profile_name="warehouse",
            target_name="dev",
            profiles_yml_filepath=project / "profiles.yml",
        ),
        execution_config=ExecutionConfig(dbt_executable_path=DBT),
        schedule=schedule,
        start_date=datetime(2026, 1, 1),
        catchup=False,
        tags=[team, "dbt"],
    )
