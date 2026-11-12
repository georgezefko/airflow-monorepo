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

## One-time setup

Run once, by someone with owner rights on the project.

```bash
P=project-09344e23-c1cd-49df-a40
PN=147789725218                       # gcloud projects describe $P --format='value(projectNumber)'
REPO=georgezefko/airflow-monorepo
SA=ci-dbt@$P.iam.gserviceaccount.com

# APIs used for the token exchange
gcloud services enable iamcredentials.googleapis.com sts.googleapis.com --project $P

# A service account just for CI
gcloud iam service-accounts create ci-dbt --project $P --display-name "CI dbt builds"

# What CI may do in BigQuery
gcloud projects add-iam-policy-binding $P --member serviceAccount:$SA --role roles/bigquery.user
gcloud projects add-iam-policy-binding $P --member serviceAccount:$SA --role roles/bigquery.dataViewer

# Trust GitHub's tokens, but only from this repository
gcloud iam workload-identity-pools create github --location global --project $P
gcloud iam workload-identity-pools providers create-oidc github \
  --location global --workload-identity-pool github --project $P \
  --issuer-uri https://token.actions.githubusercontent.com \
  --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition "assertion.repository=='$REPO'"

# Let runs from this repository act as the CI service account
gcloud iam service-accounts add-iam-policy-binding $SA --project $P \
  --role roles/iam.workloadIdentityUser \
  --member "principalSet://iam.googleapis.com/projects/$PN/locations/global/workloadIdentityPools/github/attribute.repository/$REPO"
```

`--attribute-condition` is the important line. Without it, a token from any GitHub repository
could be accepted.

## Checking the setup

```bash
# The provider: should be ACTIVE, with the repository condition
gcloud iam workload-identity-pools providers describe github \
  --location global --workload-identity-pool github --project $P \
  --format='yaml(state,attributeCondition)'

# Who may act as ci-dbt: only this repository
gcloud iam service-accounts get-iam-policy $SA --project $P

# The roles ci-dbt has on the project
gcloud projects get-iam-policy $P --flatten='bindings[].members' \
  --filter="bindings.members:$SA" --format='value(bindings.role)'
```

## Using it in a workflow

```yaml
permissions:
  contents: read
  id-token: write   # lets the job request GitHub's token

steps:
  - uses: google-github-actions/auth@v2
    with:
      workload_identity_provider: projects/147789725218/locations/global/workloadIdentityPools/github/providers/github
      service_account: ci-dbt@project-09344e23-c1cd-49df-a40.iam.gserviceaccount.com
```

The action writes a short-lived credentials file and points `GOOGLE_APPLICATION_CREDENTIALS` at
it. Our profile uses `method: oauth`, which picks that file up, so dbt needs no other changes.

The project ID, project number and service account email aren't secrets. They're useless without a
token that GCP accepts.

## Limits

- **PRs from forks don't get a token.** GitHub doesn't give `id-token: write` to workflows from
  forks, so those PRs can only run the checks that don't need GCP.
- **Rights apply to the whole project.** `bigquery.dataViewer` can read every dataset in the
  project. For tighter control, grant it on the `analytics_*` datasets only.
