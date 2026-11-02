from pathlib import Path

from airflow.models import DagBag

DAGS_DIR = Path(__file__).parents[2] / "dags"


def test_dags_import_cleanly():
    bag = DagBag(dag_folder=DAGS_DIR)
    assert not bag.import_errors, bag.import_errors
    assert bag.dags, "no DAGs found"
