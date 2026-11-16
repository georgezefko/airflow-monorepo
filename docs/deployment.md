# What a deployment needs from this repo

This repo produces code and one image; the data platform repo deploys them (Helm values, Argo CD,
one folder per environment). This page is the contract between the two. How versions are made:
[`release-flow.md`](release-flow.md).

## The image

| | |
|---|---|
| Image | `us-central1-docker.pkg.dev/project-09344e23-c1cd-49df-a40/airflow-monorepo/airflow:<airflow version>-<short sha>`, e.g. `airflow:3.3.2-385e98c` |
| Built by | [`build.yaml`](../.github/workflows/build.yaml), on every push to `main` that changes `Dockerfile`, `.dockerignore`, `plugins/`, `pyproject.toml` or `uv.lock` |
| Contains | Airflow 3.3.2, Cosmos, the dbt CLI in `/home/airflow/dbt-venv/bin/dbt`, and `plugins/` (the shared DAG helper) |
| dbt version | Exactly what `uv.lock` pins, every package: the same dbt CI's slim build runs. Upgrade dbt with `pyproject.toml` and `uv lock` |
| Doesn't contain | Teams' DAGs, dbt models and SQL: they come from the DAG bundles |
| Tags | `<airflow version>-<short sha>` of the commit that built it. Tags are never overwritten, so a tag always means the same image |

Every Airflow component runs this image: API server, scheduler, DAG processor, triggerer, and
the task pods (KubernetesExecutor: one pod per task).

On `kind`, load the image into the cluster (`docker pull`, then `kind load docker-image`) instead of
pulling from Artifact Registry: a registry token lasts one hour, so a pull secret would break when
a pod restarts. GKE pulls from Artifact Registry directly with Workload Identity.

## DAG bundles

One `GitDagBundle` per team, all on this repository, set in Airflow's
`[dag_processor] dag_bundle_config_list` (Helm: `config.dag_processor.dag_bundle_config_list`):

```json
[
  {"name": "platform", "classpath": "airflow.providers.git.bundles.git.GitDagBundle",
   "kwargs": {"repo_url": "https://github.com/georgezefko/airflow-monorepo.git",
              "tracking_ref": "main", "subdir": "teams/platform/dags"}},
  {"name": "sales", "classpath": "airflow.providers.git.bundles.git.GitDagBundle",
   "kwargs": {"repo_url": "https://github.com/georgezefko/airflow-monorepo.git",
              "tracking_ref": "main", "subdir": "teams/sales/dags"}},
  {"name": "marketing", "classpath": "airflow.providers.git.bundles.git.GitDagBundle",
   "kwargs": {"repo_url": "https://github.com/georgezefko/airflow-monorepo.git",
              "tracking_ref": "main", "subdir": "teams/marketing/dags"}}
]
```

| Setting | Dev | Prod |
|---|---|---|
| `name` | The team folder name; it must match, because DAG runs record their version under it | Same |
| `tracking_ref` | `main` | The team's release tag, e.g. `sales-v1.0.1` |
| `subdir` | `teams/<team>/dags` | Same |

- The bundle checks out the **whole repository** at the ref; `subdir` only says where to look for
  DAG files. Each team's DAG runs dbt from that same checkout, so DAGs, models and SQL always come
  from one commit.
- Each DAG run is pinned to the commit it started with: the worker checks out that exact version.
  Moving a ref never mixes versions within a run.
- The repository is public, so no git connection is needed. A private repository needs a git
  connection (`git_conn_id`) with a read-only token.
- Adding a team: one more entry, named after its folder.

## Environment

Set on every Airflow component (in Helm: `env`):

| Variable | Value | Why |
|---|---|---|
| `GCP_PROJECT` | The environment's GCP project, e.g. `project-09344e23-c1cd-49df-a40` for dev | `profiles.yml` needs it, and Cosmos runs `dbt ls` while parsing DAGs. Bundles have no `.env` file (locally dbt reads one; that hid this requirement once) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path of the mounted credentials file | `kind` only, see below |

The BigQuery datasets keep their names in every environment (`analytics_staging`, `analytics_sales`,
`analytics_marketing`): each environment is its own GCP project.

## BigQuery credentials

| Cluster | How |
|---|---|
| `kind` | A Secret with an Application Default Credentials file (`gcloud auth application-default login`), mounted into every Airflow pod, and `GOOGLE_APPLICATION_CREDENTIALS` pointing at it. Never put it in an image or in git. |
| GKE | Workload Identity: the Airflow service account is bound to a GCP service account with BigQuery rights. No file, no Secret. |

dbt's profile uses `method: oauth`, which picks up either, so nothing changes in this repo.

## What changes per release

| Event | Change in the data platform repo |
|---|---|
| Merge to `main` (any team) | Nothing: dev bundles track `main` |
| Platform changes `Dockerfile`, `plugins/` or the dbt version (`uv.lock`) | Dev's image tag → the new `airflow:<airflow version>-<short sha>` |
| A team releases, e.g. `sales-v1.0.2` | Prod: that team's `tracking_ref` → `sales-v1.0.2`, nothing else |
| Rollback | Prod: the team's `tracking_ref` → its previous tag |
