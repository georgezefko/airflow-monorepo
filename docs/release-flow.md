# Release flow

How a change gets from a PR to dev, and from dev to prod, with each team releasing on its own
schedule. Diagram: [`diagrams/deploy-flow.drawio`](diagrams/deploy-flow.drawio).

| Step | Status |
|---|---|
| 1. Conventional PR titles, squash merges | Done |
| 2. One folder per team (`teams/<team>/`), one dbt project | Done |
| 3. Dev: a dbt image per merge | Done; the manifest upload to GCS is planned |
| 4. release-please: a release PR per team | In progress |
| 5. Promote a release to prod | Planned |

## The short version

1. **Open a PR with a conventional title**, e.g. `feat(sales): add daily_revenue`. A check rejects
   other titles.
2. **Squash-merge it.** The PR title becomes the one commit on `main`.
3. **Dev updates by itself.** CI builds the team's image, tagged with the commit SHA, and dev runs
   it a few minutes later.
4. **release-please keeps a release PR open for your team**, e.g. `chore(main): release sales
   1.5.0`, with the changelog written from the commit titles.
5. **Merge your release PR when you want to go to prod.** That creates the tag `sales-v1.5.0`,
   and the prod promotion moves only your team to it.

No team waits for another: dev takes every merge, and each team decides when its own code reaches
prod.

## Repository layout

Everything a team owns is in one folder, so a team's release covers exactly that folder.

```
dbt_project.yml  profiles.yml   one dbt project, "warehouse", owned by platform
macros/                         shared dbt macros
plugins/dbt_team_dag.py         shared DAG helper
tests/                          DAG rules for every team, run once per team
teams/
  platform/  dags/  dbt/        staging models, read by every team
  sales/     dags/  dbt/
  marketing/ dags/  dbt/
```

- **One dbt project, models in team folders.** `ref()` and lineage work across teams, and a
  platform PR that changes `stg_orders` rebuilds sales' and marketing's models in CI. The dataset
  comes from the folder: `teams/sales/dbt/` builds into `analytics_sales`.
- **One DAG bundle per team**, reading only `teams/<team>/dags/`. A team's DAG runs only its own
  models (`path:teams/<team>/dbt`).
- **Shared files stay outside `teams/`.** Platform owns them. They belong to no team's release, so
  a change to them reaches prod with each team's next release.
- **Later:** `teams/<team>/apps/<app>/` for containerised apps (shared apps go under `platform`),
  `teams/<team>/sql/` for plain queries and `teams/<team>/tests/` for team-specific tests.

Adding a team: create `teams/<team>/dags` and `teams/<team>/dbt`, add the folder to `model-paths`
in `dbt_project.yml` and add a DAG bundle for it.

## 1. PR titles

The PR title must look like `type(scope): description`. The check is
[`.github/workflows/pr-title.yaml`](../.github/workflows/pr-title.yaml).

| Type | Use for | Release |
|---|---|---|
| `feat` | New model, column, DAG or behaviour | Minor: 1.4.0 → 1.5.0 |
| `fix` | A bug fix | Patch: 1.4.0 → 1.4.1 |
| `perf` | Same result, cheaper or faster | Patch |
| `revert` | Undo an earlier commit | Patch |
| `feat!`, `fix!` | A breaking change, e.g. a renamed or removed column others read | Major: 1.4.0 → 2.0.0 |
| `refactor`, `docs`, `test`, `ci`, `build`, `chore` | Everything else | None |

| Scope | When |
|---|---|
| `platform`, `sales`, `marketing` | The change is in that team's folder |
| No scope | Repository-wide changes: CI, docs, tooling |

Examples:

```
feat(sales): add daily_revenue
fix(marketing): count each event once in fct_events
feat(platform)!: rename stg_orders.id to order_id
ci: build only the teams that changed
docs: explain the release flow
```

Keep a PR to one team. A PR that changes two team folders shows up in both teams' changelogs.

**Why titles and not every commit:** with squash merges, only the PR title reaches `main`, so
commits on your branch can say anything ("wip", "fix typo"). The check runs again when you edit
the title, so a failing PR is fixed by renaming it, with no new commit.

### The alternative: conventional commit messages

The other common setup checks every commit instead of the PR title, and keeps all of them on
`main` with rebase or merge commits. We chose PR titles, but both work with release-please.

| | PR title + squash (ours) | Every commit message |
|---|---|---|
| What reaches `main` | One commit per PR, titled with the PR title | Every commit on the branch |
| Rules on the branch | None | Every commit must be conventional, checked in CI (commitlint) and often in a git hook |
| Fixing a mistake | Rename the PR; the check reruns | Rewrite history (`git rebase -i`) and force-push |
| Changelog | One entry per PR | One entry per commit, including small ones |
| Who must know the rules | Whoever opens the PR | Every contributor, on every commit |
| Undoing a change | Revert one commit | Find and revert several commits |

Commit messages fit projects where commits are the unit of review, with small curated commits
rebased onto `main`. PR titles fit teams where the PR is what gets reviewed, approved and
deployed, which is the case here.

With PR titles, a PR that holds a feature and a fix becomes one changelog entry. That usually
means the PR should be split. If not, release-please can also read extra conventional lines from
the commit body, which is the PR description, because we squash with `PR_BODY`. Check the
result in the release PR before relying on it.

## 2. Squash merges

The repository allows only squash merges, and uses the PR title as the commit title and the PR
description as its body. Every commit on `main` is therefore one reviewed PR with a conventional
title, which is what release-please reads.

Repository settings (General → Pull Requests): squash merging only, default message "Pull request
title and description", and "Automatically delete head branches". The `main` ruleset allows only
the squash method and requires the `checks` and `pr-title` status checks.

## 3. Dev: every merge

`build.yaml` runs on every push to `main` that changes dbt code. It builds one dbt image with every
team's models, tags it with the commit SHA and pushes it to Artifact Registry. Image tags can't be
overwritten, so a SHA always means the same image. Each team's prod release later pins the image
of its release commit, and that team's DAG runs only its own models from it. How CI signs in:
[`ci-gcp-auth.md`](ci-gcp-auth.md) and [`gcp-setup.md`](gcp-setup.md).

DAG-only changes don't build an image. Airflow reads DAG code from git.

## 4. Release PRs (release-please)

[release-please](https://github.com/googleapis/release-please) runs on every push to `main`. For
each team folder it reads the commits since the team's last tag that changed files in that folder.
It routes by path, not by scope. If it finds a `feat`, `fix`, `perf`, `revert` or breaking change, it opens
or updates that team's release PR, which:

- bumps the team's version in `.release-please-manifest.json` and `teams/<team>/version.txt`;
- adds entries to `teams/<team>/CHANGELOG.md`.

The release PR is titled `chore(<team>): release <version>`, which passes the PR title check.
Merging it creates the tag (`sales-v1.5.0`) and a GitHub release with the same notes. Until then,
more merges just update the PR. A version means "ready for prod"; every merge already runs in dev
by its commit SHA.

| File | What it holds |
|---|---|
| [`release-please-config.json`](../release-please-config.json) | One package per team folder; one release PR each |
| [`.release-please-manifest.json`](../.release-please-manifest.json) | Each team's current version, updated by release PRs |
| [`release-please.yaml`](../.github/workflows/release-please.yaml) | Runs release-please on every push to `main` |

`bootstrap-sha` in the config is the commit that created `teams/`. release-please ignores older
commits, whose titles weren't conventional yet. Every team starts at 1.0.0.

### How the version is chosen

release-please compares with the team's **last release**, not with the open release PR. It
collects every commit in the team's folder since that release and takes the biggest bump:

| Team commits since the last release | Release PR |
|---|---|
| `fix: A` | 1.0.0 → **1.0.1** |
| `fix: A`, `fix: B` | still **1.0.1**; the changelog lists both |
| `fix: A`, `fix: B`, `feat: C` | **1.1.0**: a feature outranks fixes |
| …and a `feat!: D` | **2.0.0** |

A team has at most one open release PR. More merges update it; they don't open new ones or bump
the version once per commit.

### Several attempts before a release

A fix that doesn't work in dev never gets a version, because only merging the release PR creates
one:

1. Merge `fix(sales): A`. Dev runs it, and the release PR shows 1.0.1 with fix A.
2. Testing in dev shows it isn't enough.
3. Merge `fix(sales): B`. Dev runs it, and the release PR still shows 1.0.1, now with A and B.
4. When it works in dev, merge the release PR: `sales-v1.0.1` contains A and B.

If a fix was wrong rather than incomplete, undo it with `git revert` (its PR titled
`revert: fix(sales): A`) before the next attempt. The changelog then shows what was tried and
undone.

### The GitHub App

release-please needs a GitHub App token, not the built-in `GITHUB_TOKEN`. GitHub doesn't run
workflows for PRs and tags created with `GITHUB_TOKEN`, so the release PR would never get the
required checks and couldn't be merged.

The workflow exchanges the App's private key for a token that's valid for one hour and only for
this repository.

#### One-time setup

Done once, by a repository admin, in the GitHub UI.

**1. Create the App.** Open https://github.com/settings/apps/new (profile picture → **Settings**
→ **Developer settings** → **GitHub Apps** → **New GitHub App**) and fill in:

| Field | Value |
|---|---|
| GitHub App name | `airflow-monorepo-release` (must be unique across GitHub; add a suffix if taken) |
| Homepage URL | `https://github.com/georgezefko/airflow-monorepo` |
| Identifying and authorizing users, Post installation | Leave empty |
| Webhook → Active | Untick |
| Where can this GitHub App be installed? | Only on this account |

Under **Permissions → Repository permissions**, set only these and leave the rest at *No access*
(*Metadata: Read-only* is added automatically):

| Permission | Access | Used for |
|---|---|---|
| Contents | Read and write | Committing changelogs, creating tags and releases |
| Issues | Read and write | Labels on release PRs (`autorelease: pending`) |
| Pull requests | Read and write | Opening and updating release PRs |

Click **Create GitHub App**.

**2. Copy the Client ID and generate a key.** On the App's page, copy the **Client ID** (starts
with `Iv`). At the bottom, **Generate a private key** downloads a `.pem` file.

**3. Install the App.** In the App's left menu: **Install App** → **Install** → **Only select
repositories** → `airflow-monorepo`.

**4. Store both in the repository**, then delete the downloaded key, so it exists only in
GitHub's secret store:

```bash
gh variable set RELEASE_APP_CLIENT_ID --body <client id>
gh secret set RELEASE_APP_PRIVATE_KEY < ~/Downloads/<app-name>.<date>.private-key.pem
rm ~/Downloads/<app-name>.<date>.private-key.pem
```

The Client ID isn't secret, so it's a variable. The private key is a secret: anyone with it can act
as the App on this repository.

#### Checking the setup

```bash
gh variable list   # RELEASE_APP_CLIENT_ID with its value
gh secret list     # RELEASE_APP_PRIVATE_KEY, without a value: GitHub never shows it
```

Whether the App is installed only shows when the workflow runs. Merge a PR whose title isn't
releasable (for example `ci: …`) and watch the **Release** run:

```bash
gh run watch $(gh run list --workflow release-please.yaml --limit 1 --json databaseId -q '.[0].databaseId')
```

It should pass and open no release PR.

| Error | Cause | Fix |
|---|---|---|
| `create-github-app-token`: `Not Found` or `Integration not found` | The App isn't installed on this repository | Repeat step 3 |
| `create-github-app-token`: `A JSON web token could not be decoded` | Wrong or incomplete private key, or a wrong Client ID | Generate a new key and repeat step 4 |
| `release-please`: `Resource not accessible by integration` | A permission is missing | Check the three permissions on the App's page, then accept the change under the installation's settings |

**Rotating the key:** generate a new key on the App's page, run `gh secret set` again, then
delete the old key there.

## 5. Prod: one team at a time

A release doesn't rebuild anything. The release workflow adds the tag `sales-v1.5.0` to the image
already built and running in dev for that commit, so prod runs exactly what dev tested. Then it
opens a PR in the deploy repo that moves only sales to `sales-v1.5.0`. Merging it deploys; moving
the tag back is the rollback.

## Hotfixes and rollbacks

This is trunk-based development: short-lived branches, `main` always deployable, releases cut by
tagging `main`. Release branches exist only for the one case below that needs them.

| Situation | Action | Code change |
|---|---|---|
| Broken in prod | Move the team's tag back in the deploy repo | None |
| Fix ready, `main` releasable | `fix(<team>): …` on `main`, then merge the release PR | A normal PR |
| Fix didn't work in dev | Another `fix(<team>): …`; it joins the same release PR | A normal PR |
| Broken after a release | Roll back, fix, release the next patch version | A normal PR |
| Fix ready, but `main` has team work that can't ship yet | Release branch from the tag, cherry-pick, release | The exception |
| Bad data was written | Roll back, rerun, full-refresh affected incremental models | None |

### Roll back first

When prod is broken, move the team back to its previous release in the deploy repo, for example
`sales: sales-v1.4.0` instead of `sales-v1.5.0`. Nothing is built: the old image still exists,
because tags are immutable. Then fix calmly.

### Fix forward (the default)

1. Open a PR titled `fix(sales): …` and squash-merge it. It runs in dev minutes later.
2. release-please adds the fix to the open sales release PR, or opens one if there isn't one.
3. Test in dev. If it isn't fixed yet, merge another `fix(sales): …`: it joins the same release
   PR (see [Several attempts before a release](#several-attempts-before-a-release)).
4. Merge the release PR and promote it.

A sales release contains only sales' own unreleased commits. Other teams' unfinished work on
`main` doesn't ship with it, because prod pins each team separately.

### A fix after a release

Released versions never change: tags and images are immutable, so a correction always gets a new
version. Say `sales-v1.5.0` is in prod and turns out broken:

1. Roll back: move sales to `sales-v1.4.0` in the deploy repo.
2. Merge `fix(sales): …`. release-please compares with `sales-v1.5.0` and opens a **new** release
   PR, `chore(sales): release 1.5.1`.
3. Test in dev, merge the release PR, and promote `sales-v1.5.1`.

### Release branch (the exception)

Only when sales' own unreleased work on `main` must not reach prod yet:

1. Create `release/sales-1.5.x` from the tag prod runs, `sales-v1.5.0`.
2. Cherry-pick the fix onto it and release `sales-v1.5.1` from that branch.
3. Make sure the fix is also on `main`, or the next normal release brings the bug back.

This isn't set up yet, and it costs:
- **A build from a branch other than `main`.** `build.yaml` runs only on `main`, and `ci-build`
  trusts only `main` ([`gcp-setup.md`](gcp-setup.md)), so release branches need their own binding.
- **No dev testing.** Dev runs `main`, so the branch build isn't tested there.
- **The fix lands twice.**

Avoid it by keeping `main` releasable: small PRs, new dbt models merged with `enabled: false`
until they're ready, and new DAGs left paused.

### Data doesn't roll back

Rolling back an image doesn't undo what it wrote to BigQuery:

- **Tables and views** are rebuilt on the next run, so running the previous release repairs them.
- **Incremental models**, such as `fct_events`, keep the bad rows. Rerun them with
  `--full-refresh`, or rebuild the affected partitions.

### Breaking changes between teams

A `feat!` in a model other teams read, such as a renamed column in platform's staging, breaks
them when it's released. Add the new column first, release, let the other teams switch in their
own releases, and remove the old column in a later release.
