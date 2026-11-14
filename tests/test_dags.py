"""Rules every team's DAGs must follow, checked once per team folder (teams/<team>/dags).

A failure names the team, e.g. test_dags_import_cleanly[sales]. Team-specific tests go in
teams/<team>/tests/.
"""
from pathlib import Path

import pytest
from airflow.dag_processing.dagbag import BundleDagBag

TEAMS = sorted(p.parent for p in (Path(__file__).parents[1] / "teams").glob("*/dags"))


def dag_bag(team_dags, safe_mode=False):
    # Each team folder is its own DAG bundle, as in Airflow
    return BundleDagBag(dag_folder=team_dags, bundle_path=team_dags, safe_mode=safe_mode)


@pytest.fixture(params=TEAMS, ids=[t.name for t in TEAMS])
def team_dags(request):
    return request.param / "dags"


def test_every_team_folder_is_found():
    assert {t.name for t in TEAMS} >= {"platform", "sales", "marketing"}


def test_dags_import_cleanly(team_dags):
    bag = dag_bag(team_dags)
    assert not bag.import_errors, bag.import_errors
    assert bag.dags, "no DAGs found"


def test_airflow_discovers_every_dag(team_dags):
    # Safe mode skips files without the words "airflow" and "dag"
    assert set(dag_bag(team_dags, safe_mode=True).dags) == set(dag_bag(team_dags).dags)


def test_every_dag_runs_dbt_models(team_dags):
    for dag_id, dag in dag_bag(team_dags).dags.items():
        assert any("run" in task.task_id for task in dag.tasks), f"{dag_id} selects no dbt models"
