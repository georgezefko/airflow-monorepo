from pathlib import Path

from airflow.dag_processing.dagbag import BundleDagBag

DAGS = Path("/opt/airflow/dags")


def test_dags_import_cleanly():
    bag = BundleDagBag(dag_folder=DAGS, bundle_path=DAGS, safe_mode=False)
    assert not bag.import_errors, bag.import_errors
    assert bag.dags, "no DAGs found"


def test_airflow_discovers_every_dag():
    all_dags = BundleDagBag(dag_folder=DAGS, bundle_path=DAGS, safe_mode=False).dags
    discovered = BundleDagBag(dag_folder=DAGS, bundle_path=DAGS).dags
    assert set(discovered) == set(all_dags)