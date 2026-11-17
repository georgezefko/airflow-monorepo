# Release flow

How a change gets from a PR to dev, and from dev to prod, with each team releasing on its own
schedule. Diagram: [`diagrams/deploy-flow.drawio`](diagrams/deploy-flow.drawio). What a deployment needs
from this repo (image, bundles, environment): [`deployment.md`](deployment.md). What has been
tried on `kind` so far: [`tested-scenarios.md`](tested-scenarios.md).

| Step | Status |
|---|---|
| 1. Conventional PR titles, squash merges | Done |
| 2. One folder per team (`teams/<team>/`), one dbt project | Done |
| 3. Dev: every merge runs from `main`; the Airflow image per platform change | Done |
| 4. release-please: a release PR per team | Done |
| 5. Promote a release to prod | Planned |

## The short version

1. **Open a PR with a conventional title**, e.g. `feat(sales): add daily_revenue`. A check rejects
   other titles.
2. **Squash-merge it.** The PR title becomes the one commit on `main`.
3. **Dev updates by itself.** Dev's DAG bundles track `main`, so Airflow picks the change up a few
   minutes later.
4. **release-please keeps a release PR open for your team**, e.g. `chore(sales): release 1.5.0`,
   with the changelog written from the commit titles.
5. **Merge your release PR when you want to go to prod.** That creates the tag `sales-v1.5.0`,
   and the prod promotion points only your team's DAG bundle at it.

No team waits for another: dev takes every merge, and each team decides when its own code reaches
prod.

## Repository layout

Everything a team owns is in one folder, so a team's release covers exactly that folder.

```
dbt_project.yml  profiles.yml   one dbt project, "warehouse", owned by platform
macros/                         shared dbt macros
tests/                          DAG rules for every team, run once per team
teams/
  platform/  dags/  dbt/        staging models, read by every team
             lib/               shared DAG helpers, imported by every team's DAGs
             apps/common/       shared containerised apps (bq-extract, pg-load)
  sales/     dags/  dbt/        sales_dbt, and sales_to_postgres (an app DAG)
             apps/transform/    sales' own app
             sql/               queries and DDL the app DAG passes to the common apps
  marketing/ dags/  dbt/
```

- **One dbt project, models in team folders.** `ref()` and lineage work across teams, and a
  platform PR that changes `stg_orders` rebuilds sales' and marketing's models in CI. The dataset
  comes from the folder: `teams/sales/dbt/` builds into `analytics_sales`.
- **One DAG bundle per team.** On Kubernetes it's a git checkout of the whole repository at the
  team's ref (`main` in dev, `sales-v1.5.0` in prod), with DAGs read from `teams/<team>/dags/`. The
  team's DAG runs dbt from that same checkout and selects only its own models
  (`path:teams/<team>/dbt`), so DAGs, models and SQL always come from one commit.
- **What's an image and what isn't.** Teams' DAGs, dbt models and SQL are never in an image; they
  come from the bundle. The only images are platform's Airflow image (Airflow, Cosmos and the dbt
  CLI) and the containerised apps in `teams/<team>/apps/`, one image each.
- **Shared DAG helpers are in `teams/platform/lib/`, not the image.** Each team's DAG imports them
  from its own checkout, so a team's tag pins the helpers it was tested with, and a rollback brings
  them back too.
- **Shared files stay outside `teams/`.** Platform owns them. They belong to no team's release, so
  a change to them reaches prod with each team's next release.
- **Apps: `teams/<team>/apps/<app>/`**, each with its own `Dockerfile`, `pyproject.toml` and
  `uv.lock`. Shared apps are platform's, in `teams/platform/apps/common/`. An image's tag is a hash
  of its folder, so a team's tag pins the images too (see
  [`deployment.md`](deployment.md#app-images)).
- **`teams/<team>/sql/`** holds queries that DAGs pass to apps, e.g. sales' extract for
  `bq-extract`. A query change is a team release; no image is built.
- **Later:** `teams/<team>/tests/` for team-specific tests.

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
the squash method and requires the `checks` and `pr-title` status checks, with "Require branches
to be up to date before merging" on.

### Conflicts between PRs

Two PRs that change the same file only conflict when they change the same or neighbouring lines.
Team folders keep that rare: teams don't edit each other's files, so conflicts are within one team.

- **The common one: two columns added at the end of a model.** Both PRs add a comma to the last
  column and a line after it:

  ```sql
      delivered_at,      -- PR A and PR B both change this line
      num_of_item        -- PR A
      returned_at        -- PR B
  ```

  Whoever merges second rebases on `main`, keeps both columns and pushes; CI runs again.
  Adding columns where they belong rather than always at the end spreads edits out.
- **The one git can't see.** PR A renames a column, PR B starts using the old name. Both pass CI
  on their own and break `main` together. That's why the ruleset requires an up-to-date branch:
  after A merges, GitHub blocks B until it's rebased on `main` and CI passes again, now with A
  in it.

Requiring up-to-date branches costs a rebase and a CI run each time `main` moves. With many PRs
merging a day, a merge queue does that rebasing and testing instead.

**Release PRs: never update them by hand.** release-please rewrites every open release PR from
`main` on each push to `main`, so after one merges, wait for the Release workflow to finish and the
others are up to date. Don't press "Update branch" or merge `main` into them. Each release PR
changes its own line of `.release-please-manifest.json`, and those lines are adjacent, so a
manual merge conflicts there. That happened with platform 1.2.0: the conflict was resolved by
keeping `main`'s side, so the tag `platform-v1.2.0` was created, but the manifest stayed at
`1.1.0`. release-please reads the last version from the manifest, so it opened platform 1.2.0
again. The fix was a `chore` PR that set the manifest to `1.2.0`, and closing the duplicate.

## 3. Dev: every merge

Dev's DAG bundles track `main`. After a merge, Airflow fetches the new commit and parses the DAGs
from it; Cosmos lists each team's models with `dbt ls` from the same checkout and caches the result
per version. Nothing is built for a team's change: DAGs, dbt models and SQL all come from git.

A bundle is versioned by commit: when a task starts, the worker checks out the exact commit its
DAG run started with. Moving a ref never mixes code from two versions within one run.

`build.yaml` builds only the platform's Airflow image, `airflow:<sha>`, when `Dockerfile` or
`plugins/` change, and pushes it to Artifact Registry. Tags can't be overwritten, so a SHA always
means the same image. How CI signs in: [`ci-gcp-auth.md`](ci-gcp-auth.md) and
[`gcp-setup.md`](gcp-setup.md).

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

A release doesn't build anything: the git tag `sales-v1.5.0` is the release. Prod's sales bundle
has `tracking_ref: sales-v1.5.0`, so prod runs exactly the commit that ran in dev. Promoting is a
PR in the deploy repo that changes only that line; moving it back is the rollback. The other
teams' bundles keep their own refs.

The Airflow image is shared by every team and promoted separately, by platform.

Each DAG has its team's version as a tag (`v1.5.0`), read from `teams/<team>/version.txt` in the
bundle's checkout, so the Airflow UI shows which release every team runs in each environment.

**In dev, the chip shows the last release, not what's running.** `version.txt` only changes when
the release PR is merged. While sales' release PR for 1.2.0 is open, dev already runs the code
that will be 1.2.0 (dev runs `main`), but its DAGs still show `v1.1.0`. After the release PR is
merged, they show `v1.2.0`. In prod the chip is exact: the tag and `version.txt` are the same
commit.

So merging the release PR doesn't change what dev runs. It marks the code on `main` as a release:
it creates the tag prod can point at and the changelog, and updates the chip.

### A team's first tag

A team that has never had a release PR merged, like platform and marketing at 1.0.0, has no tag
for prod to point at. Create it once by hand, on the commit that is 1.0.0:

```bash
git tag marketing-v1.0.0 origin/main
git push origin marketing-v1.0.0
```

After that, release-please creates every tag.

### Shared code: pinned by each team's tag, or in the image

| Shared code | Ships in | Who decides when it reaches prod |
|---|---|---|
| DAG helpers (`teams/platform/lib/`) | Every team's bundle checkout | Each team, with its next release |
| Shared apps (`teams/platform/apps/common/`) | An image per app, its tag computed from each team's checkout | Each team, with its next release |
| Airflow, Cosmos, the dbt CLI (`Dockerfile`, `uv.lock`) | The Airflow image | Platform, for every team at once |

**Helpers.** Each team's DAG adds `teams/platform/lib` from its own checkout to `sys.path`:

```python
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "teams" / "platform" / "lib"))
from dbt_team_dag import team_dag  # noqa: E402
```

Prod sales on `sales-v1.2.0` uses the helpers as they were at that tag, even after platform
changes them. A helper change reaches sales with sales' next release, after sales' CI and dev have
run it. It's listed in platform's changelog (the file is under `teams/platform`), not in the
changelogs of the teams that pick it up. Platform can't push an urgent helper fix to everyone:
each team has to release.

**The image.** `Dockerfile` and `uv.lock` are outside `teams/`, so release-please opens no release
PR for them. A change there builds a new Airflow image: platform sets it in dev, then in prod. No
team's `tracking_ref` changes. Every team runs on that one image, whatever its tag, so an upgrade
of Cosmos or Airflow must still work with the helpers in older tags that prod runs.

**`plugins/` is legacy.** Tags from before the move (`*-v1.1.0` and older) import the helper from
the image's `/opt/airflow/plugins`. It stays in the image until every team's prod tag includes the
move, then `plugins/` and its `COPY` line in the `Dockerfile` are deleted. The `sys.path.insert(0,
…)` makes the checkout's copy win in the meantime; `test_helpers_come_from_the_checkout_not_the_image`
checks it.

## Known limits

- **No dbt manifest is stored.** Airflow runs `dbt ls` on each bundle's checkout when it parses
  the DAG, and Cosmos caches the result per bundle version. CI runs `dbt parse` on `main` to get
  the manifest it compares with. Nothing goes to GCS.
- **CI compares with dev, not prod.** The slim build (`state:modified+ --defer`) defers to `main`'s
  manifest and the `analytics_*` tables dev builds. It proves the change builds on top of `main`, not
  that it works with the older team releases prod runs.
- **Within an environment, teams share tables.** In prod, sales on an old tag reads the staging
  tables that platform's current prod release builds. A tag pins code, not data: sales' checkout
  contains the staging SQL from its own commit, but sales' DAG builds only `teams/sales/dbt`, so
  `ref('stg_orders')` just names the table platform's prod release built.
- **A renamed model fails silently.** dbt doesn't drop the old table, so a team still on an old tag
  keeps reading it and runs green on data that stopped updating. Drop the old table only after
  every team's prod release has moved to the new name. That's why breaking changes need the steps in
  [Breaking changes between teams](#breaking-changes-between-teams).

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
the sales bundle's `tracking_ref: sales-v1.4.0` instead of `sales-v1.5.0`. Nothing is built: the
old tag still points at the same commit. Then fix calmly.

### Rollback and app images

A rollback brings back the app images too, and nothing has to record which image goes with which
release: the tag is computed from the code. Prod sales moving from `sales-v1.2.0` back to
`sales-v1.1.0`:

1. The bundle checks out `sales-v1.1.0`: the whole repository at that commit, including
   `teams/platform/apps/common/bq-extract/` and `teams/platform/lib/app_task.py`.
2. The DAG imports `app_task` from that checkout, like the dbt helper.
3. `app_task` hashes `bq-extract/` in that checkout. Its files are what they were at 1.1.0, so the
   hash is the one CI computed when that code was merged.
4. The pod runs `bq-extract:<that hash>`. Tags are immutable, so it's the same image.

| Must hold | Why it does |
|---|---|
| The image was pushed | Release tags are commits on `main`, and `apps.yaml` pushes every app change on `main` |
| It's still in the registry | Only while retention keeps it: the registry's cleanup policy is the rollback window |
| It's on the node (`kind` only) | After changing a `tracking_ref`, run `make airflow-image` in the data platform repo: it loads the images of every ref in the values. GKE pulls them |
| A run doesn't switch halfway | Each DAG run keeps the commit it started with, even if the ref moves |

To see which images a tag runs, check it out and list them:

```bash
git worktree add /tmp/sales-v1.2.0 sales-v1.2.0 && python3 /tmp/sales-v1.2.0/teams/platform/lib/app_image.py
```

The task log shows the image a run used (`'image': '…/bq-extract:0226adca3b6a'` in the pod spec),
and `test_app_tasks_run_this_checkouts_images` fails if a DAG stops using its own checkout's hash.

### Fix forward (the default)

1. Open a PR titled `fix(sales): …` and squash-merge it. It runs in dev minutes later.
2. release-please adds the fix to the open sales release PR, or opens one if there isn't one.
3. Test in dev. If it isn't fixed yet, merge another `fix(sales): …`: it joins the same release
   PR (see [Several attempts before a release](#several-attempts-before-a-release)).
4. Merge the release PR and promote it.

A sales release contains only sales' own unreleased commits. Other teams' unfinished work on
`main` doesn't ship with it, because prod pins each team separately.

### A fix after a release

Released versions never change: a release tag always points at the same commit, so a correction
always gets a new version. Say `sales-v1.5.0` is in prod and turns out broken:

1. Roll back: move sales to `sales-v1.4.0` in the deploy repo.
2. Merge `fix(sales): …`. release-please compares with `sales-v1.5.0` and opens a **new** release
   PR, `chore(sales): release 1.5.1`.
3. Test in dev, merge the release PR, and promote `sales-v1.5.1`.

### Release branch (the exception)

Only when sales' own unreleased work on `main` must not reach prod yet:

1. Create `release/sales-1.5.x` from the tag prod runs, `sales-v1.5.0`.
2. Cherry-pick the fix onto it and release `sales-v1.5.1` from that branch.
3. Make sure the fix is also on `main`, or the next normal release brings the bug back.

Nothing needs building for it: prod's bundle simply points at the new tag on the branch. It
isn't set up yet, and it costs:
- **release-please on the branch.** Its workflow runs only on `main`; release branches need it
  added, or the tag is created by hand.
- **No dev testing.** Dev runs `main`, so the branch isn't tested there.
- **The fix lands twice.**

Avoid it by keeping `main` releasable: small PRs, new dbt models merged with `enabled: false`
until they're ready, and new DAGs left paused.

### Data doesn't roll back

Rolling back a release doesn't undo what it wrote to BigQuery:

- **Tables and views** are rebuilt on the next run, so running the previous release repairs them.
- **Incremental models**, such as `fct_events`, keep the bad rows. Rerun them with
  `--full-refresh`, or rebuild the affected partitions.

### Breaking changes between teams

A `feat!` in a model other teams read, such as a renamed column in platform's staging, breaks
them when it's released. Add the new column first, release, let the other teams switch in their
own releases, and remove the old column in a later release.
