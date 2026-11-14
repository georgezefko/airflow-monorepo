# How CI signs in to GCP

CI builds the models a PR changes in BigQuery, so GitHub Actions needs to sign in to GCP. The usual
way is a service account key stored as a GitHub secret, but our GCP organisation blocks key
creation (`iam.disableServiceAccountKeyCreation`). A key is also a long-lived password that can
leak, and has to be rotated.

We use **Workload Identity Federation** instead: GCP trusts short-lived tokens that GitHub issues
to each workflow run, and only from this repository. Nothing secret is stored.

Diagram: [`diagrams/ci-gcp-auth.drawio`](diagrams/ci-gcp-auth.drawio)

## How it works

1. **The job asks GitHub for a token.** The workflow needs `permissions: id-token: write`.
2. **GitHub returns a signed token** (a JWT) with facts about the run, such as the repository,
   branch and commit. It's valid for a few minutes.
3. **The job sends the token to Google's Security Token Service**, through the `github` provider
   in the `github` identity pool.
4. **Google checks the token**: that GitHub signed it, and that the attribute condition holds
   (`repository == georgezefko/airflow-monorepo`). A token from any other repository is rejected.
5. **Google returns a federated token**, which IAM Credentials exchanges for an access token of the
   `ci-dbt` service account. That's allowed because the repository was granted
   `roles/iam.workloadIdentityUser` on it.
6. **dbt uses that access token**, which expires after about an hour, to run queries.

## What CI is allowed to do

| Role on the project | Allows | Needed for |
|---|---|---|
| `roles/bigquery.user` | Run queries and create datasets. BigQuery makes the creator a dataset's owner. | Building in `ci_pr_<n>_*` and deleting those datasets when the PR closes |
| `roles/bigquery.dataViewer` | Read every table | Reading unchanged upstream models from `analytics_*` (dbt's `--defer`) |

CI can't change or delete `analytics_*`, so a PR can't damage the shared tables.

## Pushing images: a second service account

`build.yaml` pushes the dbt image with `ci-build`, which has `roles/artifactregistry.writer` on the
`airflow-monorepo` registry and nothing else. It isn't `ci-dbt` because every PR branch may act as
`ci-dbt`: a PR could edit its workflow and push an image that later gets deployed. Only runs on
`main` may act as `ci-build`. The registry also has immutable tags, so even `main` can't replace
an image that's already pushed.

## Setup and commands

All setup and verification commands are in [`gcp-setup.md`](gcp-setup.md).

The auth action writes a short-lived credentials file and points `GOOGLE_APPLICATION_CREDENTIALS`
at it. Our profile uses `method: oauth`, which picks that file up, so dbt needs no other changes.
For `docker login`, the action also returns an access token (`token_format: access_token`).

## Limits

- **PRs from forks don't get a token.** GitHub doesn't give `id-token: write` to workflows from
  forks, so those PRs can only run the checks that don't need GCP.
- **Rights apply to the whole project.** `bigquery.dataViewer` can read every dataset in the
  project. For tighter control, grant it on the `analytics_*` datasets only.
