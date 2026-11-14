# GCP setup for CI

The one-time commands that let GitHub Actions use GCP without a key. Run them once per GCP
project, as someone with owner rights. Why it works this way: [`ci-gcp-auth.md`](ci-gcp-auth.md).

| What | Used by | Can do |
|---|---|---|
| Pool `github`, provider `github` | Both service accounts | Accept GitHub tokens from this repository only |
| `ci-dbt` | `pr.yaml` (`dbt-build`), `pr-cleanup.yaml`, on any branch | Build in `ci_pr_<n>_*`, read `analytics_*` |
| `ci-build` | `build.yaml`, on `main` only | Push images to the `airflow-monorepo` registry |
| Registry `airflow-monorepo` (`us-central1`) | `build.yaml` | Holds `airflow:<sha>` images; tags can't be overwritten |

## Variables

Every block below uses these.

```bash
P=project-09344e23-c1cd-49df-a40
PN=147789725218                       # gcloud projects describe $P --format='value(projectNumber)'
REPO=georgezefko/airflow-monorepo
REGION=us-central1
POOL=projects/$PN/locations/global/workloadIdentityPools/github
```

## 1. Trust GitHub (pool and provider)

```bash
gcloud services enable iamcredentials.googleapis.com sts.googleapis.com --project $P

gcloud iam workload-identity-pools create github --location global --project $P
gcloud iam workload-identity-pools providers create-oidc github \
  --location global --workload-identity-pool github --project $P \
  --issuer-uri https://token.actions.githubusercontent.com \
  --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition "assertion.repository=='$REPO'"
```

`--attribute-condition` rejects tokens from every other repository. Without it, any GitHub
repository could get in.

## 2. `ci-dbt`: dbt builds for PRs

```bash
SA=ci-dbt@$P.iam.gserviceaccount.com

gcloud iam service-accounts create ci-dbt --project $P --display-name "CI dbt builds"

gcloud projects add-iam-policy-binding $P --member serviceAccount:$SA --role roles/bigquery.user
gcloud projects add-iam-policy-binding $P --member serviceAccount:$SA --role roles/bigquery.dataViewer

# Any run from this repository, on any branch
gcloud iam service-accounts add-iam-policy-binding $SA --project $P \
  --role roles/iam.workloadIdentityUser \
  --member "principalSet://iam.googleapis.com/$POOL/attribute.repository/$REPO"
```

## 3. `ci-build`: images from `main`

```bash
SA=ci-build@$P.iam.gserviceaccount.com

gcloud services enable artifactregistry.googleapis.com --project $P

gcloud artifacts repositories create airflow-monorepo --project $P --location $REGION \
  --repository-format docker --immutable-tags

gcloud iam service-accounts create ci-build --project $P --display-name "CI image builds"

# Push rights on this registry only
gcloud artifacts repositories add-iam-policy-binding airflow-monorepo --project $P --location $REGION \
  --member serviceAccount:$SA --role roles/artifactregistry.writer

# The subject GitHub puts in tokens from this repository (see the note below)
SUB_PREFIX=$(gh api repos/$REPO/actions/oidc/customization/sub -q .sub_claim_prefix)
# repo:georgezefko@46191927/airflow-monorepo@1443457357

# Only runs on main. Keep the braces: in zsh, "$SUB_PREFIX:ref" applies the :r modifier
gcloud iam service-accounts add-iam-policy-binding $SA --project $P \
  --role roles/iam.workloadIdentityUser \
  --member "principal://iam.googleapis.com/$POOL/subject/${SUB_PREFIX}:ref:refs/heads/main"
```

The two bindings differ on purpose. `ci-dbt` uses `principalSet://…/attribute.repository/…`, which
matches every run from the repository, because PR branches need it. `ci-build` uses
`principal://…/subject/…`, which matches exactly one GitHub subject: runs on `main`. A PR can edit
its workflow to ask for `ci-build`, but GCP refuses the token.

The subject isn't `repo:georgezefko/airflow-monorepo:…`. The repository uses GitHub's immutable
subject (`use_immutable_subject: true`), which adds the owner and repository IDs, so a renamed or
re-created repository with the same name can't match. Always read the prefix from the API, as
above; a binding with the plain name fails with `Permission 'iam.serviceAccounts.getAccessToken'
denied`. `ci-dbt` isn't affected because it matches `attribute.repository`, which stays the plain
name.

GitHub ends the subject with `:environment:<name>` instead of `:ref:refs/heads/main` when a job
sets `environment:`. If `build.yaml` ever gets an environment, update this binding to match.

## Checking the setup

```bash
# Provider: ACTIVE, with the repository condition
gcloud iam workload-identity-pools providers describe github \
  --location global --workload-identity-pool github --project $P \
  --format='yaml(state,attributeCondition)'

# Who may act as each service account
for sa in ci-dbt ci-build; do
  gcloud iam service-accounts get-iam-policy $sa@$P.iam.gserviceaccount.com --project $P \
    --format='value(bindings.role,bindings.members)'
done

# Project roles (ci-dbt: bigquery.user and dataViewer; ci-build: none)
gcloud projects get-iam-policy $P --flatten='bindings[].members' \
  --filter='bindings.members:ci-' --format='table(bindings.members,bindings.role)'

# Registry: immutable tags, and only ci-build may push
gcloud artifacts repositories describe airflow-monorepo --project $P --location $REGION \
  --format='value(dockerConfig.immutableTags)'
gcloud artifacts repositories get-iam-policy airflow-monorepo --project $P --location $REGION \
  --format='value(bindings.role,bindings.members)'

# Images pushed so far
gcloud artifacts docker images list $REGION-docker.pkg.dev/$P/airflow-monorepo --include-tags
```

## Using them in a workflow

```yaml
permissions:
  contents: read
  id-token: write   # lets the job request GitHub's token

steps:
  - id: auth
    uses: google-github-actions/auth@v2
    with:
      workload_identity_provider: projects/147789725218/locations/global/workloadIdentityPools/github/providers/github
      service_account: ci-build@project-09344e23-c1cd-49df-a40.iam.gserviceaccount.com   # or ci-dbt
      token_format: access_token   # only for docker login; dbt reads the credentials file
```

The project ID, project number and service account emails aren't secrets. They're useless without
a token that GCP accepts.
