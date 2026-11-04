from airflow.dag_processing.dagbag import DagBag


def test_dags_import_cleanly():
    bag = DagBag(dag_folder="/opt/airflow/dags", safe_mode=False)
    assert not bag.import_errors, bag.import_errors
    assert bag.dags, "no DAGs found"