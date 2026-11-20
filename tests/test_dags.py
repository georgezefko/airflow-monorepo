"""Rules every team's DAGs must follow, checked once per team folder (teams/<team>/dags).

A failure names the team, e.g. test_dags_import_cleanly[sales]. Team-specific tests go in
teams/<team>/tests/.
"""
import sys
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


def test_helpers_come_from_the_checkout_not_the_image(team_dags):
    # Each tag pins its own helpers: they must come from this checkout, never from the image
    dag_bag(team_dags)
    import dbt_team_dag

    assert Path(dbt_team_dag.__file__).parent == Path(__file__).parents[1] / "teams" / "platform" / "lib"


def test_every_dbt_dag_runs_dbt_models(team_dags):
    dbt_dags = {d: dag for d, dag in dag_bag(team_dags).dags.items() if "dbt" in dag.tags}
    assert dbt_dags, "no dbt DAG"
    for dag_id, dag in dbt_dags.items():
        assert any("run" in task.task_id for task in dag.tasks), f"{dag_id} selects no dbt models"


def test_app_tasks_run_this_checkouts_images(team_dags):
    sys.path.insert(0, str(Path(__file__).parents[1] / "teams" / "platform" / "lib"))
    from app_image import all_apps, image

    this_checkout = {image(d) for d in all_apps(Path(__file__).parents[1])}
    for dag_id, dag in dag_bag(team_dags).dags.items():
        for task in dag.tasks:
            if hasattr(task, "image"):
                assert task.image in this_checkout, f"{dag_id}.{task.task_id} runs {task.image}"


def test_version_chip_is_the_release_or_the_configured_tag(team_dags, monkeypatch):
    version = "v" + (team_dags.parent / "version.txt").read_text().strip()
    assert all(version in dag.tags for dag in dag_bag(team_dags).dags.values())
    monkeypatch.setenv("AIRFLOW__PLATFORM__VERSION_TAG", "main")  # what dev sets
    assert all("main" in dag.tags and version not in dag.tags for dag in dag_bag(team_dags).dags.values())
