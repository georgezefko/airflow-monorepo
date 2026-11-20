# What a deployment needs from this repo

This repo produces code and one image; the data platform repo deploys them (Helm values, Argo CD,
one folder per environment). This page is the contract between the two. How versions are made:
[`release-flow.md`](release-flow.md).

## The image

| | |
|---|---|
| Image | `us-central1-docker.pkg.dev/<project>/airflow-monorepo/airflow:<airflow version>-<short sha>`, e.g. `airflow:3.3.2-385e98c`. Pushed with the same tag to each environment's registry: `project-09344e23-c1cd-49df-a40` (dev) and `tutorials-demo-prod` (prod) |
| Built by | [`build.yaml`](../.github/workflows/build.yaml), on every push to `main` that changes `Dockerfile`, `.dockerignore`, `pyproject.toml` or `uv.lock` |
| Contains | Airflow 3.3.2, Cosmos and the dbt CLI in `/home/airflow/dbt-venv/bin/dbt`. No DAG code: the shared DAG helpers come from each bundle's checkout of `teams/platform/lib/` ([why](release-flow.md#shared-code-pinned-by-each-teams-tag-or-in-the-image)) |
| dbt version | Exactly what `uv.lock` pins, every package: the same dbt CI's slim build runs. Upgrade dbt with `pyproject.toml` and `uv lock` |
| Doesn't contain | Teams' DAGs, dbt models and SQL: they come from the DAG bundles |
| Tags | `<airflow version>-<short sha>` of the commit that built it. Tags are never overwritten, so a tag always means the same image |

Every Airflow component runs this image: API server, scheduler, DAG processor, triggerer, and
the task pods (KubernetesExecutor: one pod per task).

On `kind`, load the image into the cluster (`docker pull`, then `kind load docker-image`) instead of
pulling from Artifact Registry: a registry token lasts one hour, so a pull secret would break when
a pod restarts. GKE pulls from Artifact Registry directly with Workload Identity.

## App images

Each folder with a `Dockerfile` under `teams/<team>/apps/` is one image, run by a DAG as a pod:

| | |
|---|---|
| Image | `us-central1-docker.pkg.dev/<project>/airflow-monorepo/<team>/<path>:<hash>`, e.g. `…/platform/common/bq-extract:0226adca3b6a`. Every merge pushes new tags to dev's registry ([`apps.yaml`](../.github/workflows/apps.yaml)); a team release pushes the same images to prod's ([`promote.yaml`](../.github/workflows/promote.yaml)), not rebuilt. DAGs name the registry from `APPS_REGISTRY` |
| Tag | A hash of the app folder's files ([`app_image.py`](../teams/platform/lib/app_image.py)). Same code, same tag, so a merge rebuilds nothing that's already pushed |
| Built by | [`apps.yaml`](../.github/workflows/apps.yaml): PRs check that every app builds; `main` pushes the tags that aren't in the registry yet |
| List them | `python3 teams/platform/lib/app_image.py` |

- **The DAG computes the tag from its own checkout.** Sales on `sales-v1.2.0` runs the images of
  that commit, even after platform changes `bq-extract`. A rollback to an older tag runs older
  images, so the registry must keep them: its retention is how far back you can roll back.
- **No image per branch.** PRs can't push (only `main` may act as `ci-build`). To try an app on
  `kind` before merging, build it locally with its tag and `kind load` it.
- **On `kind`**, load the images after each merge, like the Airflow image: the data platform repo's
  `scripts/app-images.sh` loads every app image of a checkout. For a team on an older tag, run it
  on a checkout of that tag. CI can't do it: it can't reach a cluster on your machine.

| App | Does | Arguments |
|---|---|---|
| `common/bq-extract` | Runs a BigQuery query, writes parquet | `--sql`, `--out` (gs:// or a path). Env: `GCP_PROJECT`, credentials as for dbt |
| `common/pg-load` | Loads parquet into a Postgres table, replacing its rows in one transaction. Creates the database if missing, then runs `--ddl` | `--in`, `--table schema.table`, `--ddl`. Env: `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` |

The query and the DDL come from the team's DAG, not the image: a team changes what it extracts
and loads with a release of its own, and no image is built.

### What app pods need from each environment

DAGs run apps with `app_task` ([`teams/platform/lib/app_task.py`](../teams/platform/lib/app_task.py)),
one `KubernetesPodOperator` each. The pods start in Airflow's namespace (the chart's default
`allowPodLaunching: true` lets task pods create them) and need:

| What | Dev | Why |
|---|---|---|
| A bucket for files between steps | `gs://<project>-airflow-data`, deleted after 7 days | Each step is its own pod: extract writes parquet, transform reads it, load reads the result |
| `config.apps.data_folder` | `gs://project-09344e23-c1cd-49df-a40-airflow-data/dev` (`/prod` for prod) | Each run writes to `<data_folder>/<dag_id>/<run_id>/` |
| Secret `analytics-postgres` | `PGHOST`, `PGUSER`, `PGPASSWORD`, `PGDATABASE=analytics_dev` | For `pg-load`; the database is created on the first load |
| Secret `airflow-gcp-adc` | The one Airflow already mounts | `kind` only; on GKE, Workload Identity |

Create the bucket once:

```bash
P=project-09344e23-c1cd-49df-a40
gcloud storage buckets create gs://${P}-airflow-data --project=$P --location=US --uniform-bucket-level-access
echo '{"rule":[{"action":{"type":"Delete"},"condition":{"age":7}}]}' > /tmp/lifecycle.json
gcloud storage buckets update gs://${P}-airflow-data --lifecycle-file=/tmp/lifecycle.json
```

The Secret, per namespace (`develop` for dev, `prod` with `PGDATABASE=analytics_prod`):

```bash
kubectl create secret generic analytics-postgres -n develop \
  --from-literal=PGHOST=postgres.develop.svc.cluster.local --from-literal=PGUSER=postgres \
  --from-literal=PGPASSWORD=postgres --from-literal=PGDATABASE=analytics_dev
```

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

Set on every Airflow component (in Helm: `env`). Set it in each environment's values file, not in
the common one: Helm replaces lists instead of merging them.

| Variable | Value | Why |
|---|---|---|
| `GCP_PROJECT` | The environment's GCP project: `project-09344e23-c1cd-49df-a40` for dev, `tutorials-demo-prod` for prod | `profiles.yml` needs it, and Cosmos runs `dbt ls` while parsing DAGs. Bundles have no `.env` file (locally dbt reads one; that hid this requirement once) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path of the mounted credentials file | `kind` only, see below |
| `APPS_REGISTRY` | The environment's app registry, e.g. `us-central1-docker.pkg.dev/tutorials-demo-prod/airflow-monorepo` for prod | App tasks name their image with it. Unset means dev's registry |

In dev only, also set this Airflow config (Helm: `config`, which merges with the common values,
unlike `env`):

```yaml
config:
  platform:
    version_tag: main   # DAGs show "main" instead of the last release's version
```

Without it, a DAG's version chip is `v<version.txt>`. That's exact in prod, where the bundle is
at a release tag, but dev runs `main`, which is usually ahead of the last release.

The BigQuery datasets keep their names in every environment (`analytics_staging`, `analytics_sales`,
`analytics_marketing`): each environment is its own GCP project.

## BigQuery credentials

| Cluster | How |
|---|---|
| `kind` | A Secret with an Application Default Credentials file (`gcloud auth application-default login`), mounted into every Airflow pod, and `GOOGLE_APPLICATION_CREDENTIALS` pointing at it. Never put it in an image or in git. |
| GKE | Workload Identity: the Airflow service account is bound to a GCP service account with BigQuery rights. No file, no Secret. |

dbt's profile uses `method: oauth`, which picks up either, so nothing changes in this repo.

## Task logs

With the KubernetesExecutor, each task runs in its own pod, and the pod is deleted when the task
ends. Without remote logging the UI can't read a finished task's log: it shows `Could not read
served logs … Failed to resolve '<pod name>'`. With remote logging, each task uploads its log to
GCS when it ends, and the UI reads it from there.

**1. Create the bucket, once per GCP project.** Logs are deleted after 30 days:

```bash
P=project-09344e23-c1cd-49df-a40
gcloud storage buckets create gs://$P-airflow-logs --project=$P --location=US --uniform-bucket-level-access
echo '{"rule":[{"action":{"type":"Delete"},"condition":{"age":30}}]}' > /tmp/lifecycle.json
gcloud storage buckets update gs://${P}-airflow-logs --lifecycle-file=/tmp/lifecycle.json
```

**2. Turn it on per environment**, in that environment's values, one folder each:

```yaml
config:
  logging:
    remote_logging: "True"
    remote_base_log_folder: gs://project-09344e23-c1cd-49df-a40-airflow-logs/dev   # /prod for prod
```

- **No connection needed.** Without `remote_log_conn_id`, the GCS handler uses the same
  credentials as dbt: the ADC file on `kind`, Workload Identity on GKE. The official image
  already includes the Google provider.
- **Restarts take a while.** Changing the config restarts every component. On `kind` the API
  server takes minutes to start, so a few `Startup probe failed … connection refused` events are
  normal. It's only a problem if the pod keeps restarting.

**3. Check it.** Run any task and open its log in the UI. The file is in
`gs://<project>-airflow-logs/<env>/dag_id=<dag>/run_id=<run>/task_id=<task>/`.

## What changes per release

| Event | Change in the data platform repo |
|---|---|
| Merge to `main` (any team) | Nothing: dev bundles track `main` |
| An app changes (`teams/*/apps/`) | Nothing: dev's checkout of `main` computes the new tag, prod gets it with each team's next release, when `promote.yaml` pushes it to prod's registry. On `kind`, load the new images (`scripts/app-images.sh` in the data platform repo) |
| Platform changes `Dockerfile` or the dbt version (`uv.lock`) | Dev's image tag → the new `airflow:<airflow version>-<short sha>` |
| A team releases, e.g. `sales-v1.0.2` | Prod: that team's `tracking_ref` → `sales-v1.0.2`, nothing else |
| Rollback | Prod: the team's `tracking_ref` → its previous tag |
