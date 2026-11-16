# Tested scenarios

The release flow from [`release-flow.md`](release-flow.md), tried end to end on `kind`. Dev's
bundles track `main`, and prod's bundles track team tags. Each DAG shows its team version as a tag
(`v1.1.0`), which is how each result was checked in the UI.

| # | Scenario | PRs | Result |
|---|---|---|---|
| 1 | Shared code ships in the image | #17 | New image, no tag moved |
| 2 | A team's first tag, by hand | none | `platform-v1.0.0`, `marketing-v1.0.0` |
| 3 | One team releases | #18, #20 | Prod sales on `sales-v1.1.0`, others unchanged |
| 4 | A change outside `teams/` | #19 | No release PR |
| 5 | Merged but not released | #21, #22 | Dev has it, prod doesn't, until the release |
| 6 | Two changes in one release | #23, #25, #24 | One release PR, 1.1.0, both changes |
| 7 | Up-to-date branches required | #25, #26 | Second PR blocked until updated |
| 8 | Spike: shared code imported from each bundle's own checkout | none (branch `spike/platform-lib`) | Each bundle got its own ref's version |

## 1. Shared code ships in the image

- **Change:** `feat: show team version as a DAG tag` (#17) changed `plugins/dbt_team_dag.py`.
- **What happened:** `plugins/` isn't in any team folder, so release-please opened no release PR.
  `build.yaml` built `airflow:3.3.2-385e98c` (it was `3.3.2-ed27682`).
- **Rollout:** `kind load`, then the new image tag in dev and, once checked there, in prod. No
  `tracking_ref` changed.
- **Check:** after the rollout, every DAG had a version tag, including on the old team tags,
  because the version is read from `version.txt` in each bundle's checkout.

## 2. A team's first tag, by hand

Only `sales-v1.0.1` existed; platform and marketing had never had a release PR merged. Both were
tagged on `main` (`385e98c`) after checking that they had no releasable commits since the
bootstrap and no open release PR. All of prod's bundles then tracked a tag, none a branch.

## 3. One team releases

1. **`feat(sales): add weekly_revenue` (#18), merged.** Dev's `sales_dbt` got the new tasks,
   still `v1.0.1`. Prod didn't change.
2. **release-please opened `chore(sales): release 1.1.0` (#20).** It changed only
   `teams/sales/version.txt`, `teams/sales/CHANGELOG.md` and the manifest.
3. **#20 merged.** That created `sales-v1.1.0`.
4. **Promotion:** only prod's sales `tracking_ref` moved, `sales-v1.0.1` → `sales-v1.1.0`.
   Platform and marketing stayed on `v1.0.0`.

## 4. A change outside `teams/`

`docs: deployment caveats for team versions` (#19) merged without opening a release PR, because
`docs/` belongs to no team. The same goes for `plugins/`, `Dockerfile`, `uv.lock` and the
workflows.

## 5. Merged but not released

1. **`feat(marketing): add orders_per_customer…` (#21), merged.** Dev's
   `orders_by_traffic_source` got the column. Prod's didn't, because prod marketing stayed on
   `marketing-v1.0.0`.
2. **The release PR waited.** `chore(marketing): release 1.1.0` (#22) stayed open while sales was
   already on 1.1.0 in prod. Neither team waited for the other, and sales' release didn't carry
   marketing's work.
3. **Released when ready.** #22 was merged later and created `marketing-v1.1.0`.

## 6. Two changes in one release

1. **`feat(platform): add shipped_at and delivered_at to stg_orders` (#23), merged.**
   release-please opened `chore(platform): release 1.1.0` (#24), which was left open.
2. **`feat(platform): add num_of_item to stg_orders` (#25), merged.** It was branched from `main`
   after #23, because it edits the same lines.
3. **#24 updated itself:** still **1.1.0**, now listing both features. release-please compares
   with the last release, `platform-v1.0.0`, and takes the biggest bump, so it's one release PR
   and one version, not one per merge.
4. **CI on both PRs:** `stg_orders` changed, so the slim build (`state:modified+`) also rebuilt
   sales' and marketing's models downstream in `ci_pr_<n>`.

Both changes only add columns, so sales and marketing on their own tags keep working when
platform's release reaches prod.

## 7. Up-to-date branches required

The `main` ruleset now has "Require branches to be up to date before merging" on. #25 and #26
were open at the same time; after #25 merged, #26 was out of date and had to be updated with
`main` and pass CI again before it could merge. Why: [Conflicts between
PRs](release-flow.md#conflicts-between-prs).

## 8. Spike: shared code imported from each bundle's own checkout

**Question:** can the DAG helpers move out of the image (`plugins/`) into `teams/platform/lib/`,
with each team's DAG importing them from its own bundle checkout?

**Setup:**
- `teams/platform/lib/hello.py` stood in for the helpers: `VERSION = "1"` at tag `spike-v1`, and
  `"2"` on the branch.
- Two temporary dev bundles ran the same DAG: `spike_a` on the tag, `spike_b` on the branch.
- Each DAG tried `import hello` with no setup, then added `<repo root>/teams/platform/lib` to
  `sys.path` and imported it again.

**Result (in the task pods):**

| | spike_a (tag `spike-v1`) | spike_b (branch) |
|---|---|---|
| Import with no setup | Fails: `No module named 'hello'` | Fails |
| `hello_version` | `1` | `2` |
| `hello_file` | `…/dag_bundles/spike_a/versions/b712ed4…/teams/platform/lib/hello.py` | `…/dag_bundles/spike_b/versions/172ecbc…/teams/platform/lib/hello.py` |

**What it shows:**
- **The checkout is the whole repo.** Each bundle version is a full checkout at
  `dag_bundles/<bundle>/versions/<sha>/`, so `teams/platform/lib` is there at the team's own ref.
- **Only the DAG folder is importable.** `sys.path` gets `…/teams/<team>/dags` and not the repo
  root, so the helpers need one path setup line.
- **Versions don't mix.** Two bundles in one cluster import different versions of the same module.
  A team's tag pins the helpers it was tested with.
- **`/opt/airflow/plugins` comes before the bundle on `sys.path`.** While the image still has
  `plugins/dbt_team_dag.py`, the path setup must insert at position 0, or the image's copy wins.
  Remove `plugins/` from the image once the helpers have moved.

## Not tested yet

- Platform release 1.1.0 in prod: merge #24, move prod's platform bundle to `platform-v1.1.0`.
- Rollback: move a team's prod `tracking_ref` back to its previous tag.
- A breaking change in staging, such as a renamed column (see [Breaking changes between
  teams](release-flow.md#breaking-changes-between-teams)).
- A fix after a release (1.1.0 → 1.1.1) and the release-branch exception.
