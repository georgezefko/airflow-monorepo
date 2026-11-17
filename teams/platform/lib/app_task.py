"""Run an app (teams/<team>/apps/<path>) as a pod, with the image of the calling DAG's checkout.

    app_task("platform/common/bq-extract", "extract", ["--sql", sql, "--out", f"{DATA}/extract.parquet"])

The image tag is the hash of the app folder in this checkout (app_image.py), so a team's release
tag pins the images it runs, like its SQL and dbt models.
"""
import os
import sys
from pathlib import Path

from airflow.configuration import conf
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from app_image import image
from kubernetes.client import models as k8s

# Where a run's apps pass files to each other, one folder per run (set per environment in Helm:
# config.apps.data_folder). run_id has ':' and '+', which object-store URIs don't like.
DATA = (
    conf.get("apps", "data_folder", fallback="gs://set-config-apps-data_folder")
    + "/{{ dag.dag_id }}/{{ run_id | replace(':', '-') | replace('+', '-') }}"
)
ADC_SECRET = "airflow-gcp-adc"  # kind only: the same credentials file Airflow's pods mount
POSTGRES_SECRET = "analytics-postgres"  # PGHOST, PGUSER, PGPASSWORD, PGDATABASE


def app_task(app, task_id, arguments, postgres=False):
    project = Path(sys._getframe(1).f_globals["__file__"]).resolve().parents[3]
    team, *path = app.split("/")
    app_dir = project / "teams" / team / "apps" / Path(*path)
    if not (app_dir / "Dockerfile").exists():
        raise ValueError(f"no app at {app_dir}")

    env = {"GCP_PROJECT": os.environ.get("GCP_PROJECT", "")}
    volumes, mounts = [], []
    adc = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if adc:  # on GKE there's no file: Workload Identity
        env["GOOGLE_APPLICATION_CREDENTIALS"] = adc
        volumes.append(k8s.V1Volume(name="gcp-adc", secret=k8s.V1SecretVolumeSource(secret_name=ADC_SECRET)))
        mounts.append(k8s.V1VolumeMount(name="gcp-adc", mount_path=str(Path(adc).parent), read_only=True))

    return KubernetesPodOperator(
        task_id=task_id,
        name=task_id,
        image=image(app_dir),
        image_pull_policy="IfNotPresent",  # kind: loaded, never pulled
        arguments=arguments,
        env_vars=env,
        env_from=[k8s.V1EnvFromSource(secret_ref=k8s.V1SecretEnvSource(name=POSTGRES_SECRET))] if postgres else None,
        volumes=volumes,
        volume_mounts=mounts,
        get_logs=True,
        on_finish_action="delete_pod",
    )
