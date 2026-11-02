# Post 1: what dbt actually does when you type `dbt run`

Runbook for the six demos. Run everything from the repo root after `make setup` and
`cp .env.example .env`. `$DBT` below means `uv run dbt --project-dir dbt --profiles-dir dbt`.

> **BigQuery sandbox won't do.** The sandbox has no DML, so the `MERGE` statements behind both
> incremental strategies fail, and it expires partitions after 60 days. Turn on billing for the
> project (the free tier still covers 1 TiB of queries and 10 GiB of storage a month) and set a
> budget alert. Demos 1, 2 and 5, and the Airflow demo with full refreshes, work without it.

## 1. Parse: the manifest is the product

```bash
rm -rf dbt/target && time $DBT parse          # cold
time $DBT parse                               # warm: partial_parse.msgpack
ls dbt/target
jq '.nodes | keys' dbt/target/manifest.json
jq '.nodes["model.thelook.fct_orders"].depends_on' dbt/target/manifest.json
jq '[.nodes[] | select(.resource_type=="test") | .name]' dbt/target/manifest.json
jq '.sources | keys' dbt/target/manifest.json
```

## 2. Compile: Jinja in, SQL out

```bash
$DBT compile -s fct_orders
diff dbt/models/marts/fct_orders.sql dbt/target/compiled/thelook/models/marts/fct_orders.sql
$DBT run -s fct_orders && cat dbt/target/run/thelook/models/marts/fct_orders.sql   # DDL wrapper

$DBT compile -s fct_orders --target prod   # ref() now points at marts.*, not dbt_<you>.*
cat dbt/macros/generate_schema_name.sql

$DBT compile -s fct_events                 # first time: is_incremental() false
$DBT run -s fct_events
$DBT compile -s fct_events                 # now: the where-clause appears
```

## 3. Materializations are just macros

```bash
ls .venv/lib/python3.12/site-packages/dbt/include/bigquery/macros/materializations/
#   incremental.sql, incremental_strategy/merge.sql, incremental_strategy/insert_overwrite.sql
cat dbt/target/run/thelook/models/marts/fct_events.sql
```

Then run `scripts/jobs_by_strategy.sql` in the console. Its `query` column holds what
BigQuery actually received: the temp table create, the `MERGE`, the `drop table`.

## 4. The experiment: four strategies, one model

```bash
$DBT build -s +fct_events --full-refresh --vars '{events_scale: 20}'   # big target first
for s in merge merge_predicates insert_overwrite_dynamic insert_overwrite_static; do
  $DBT run -s fct_events --vars "{events_strategy: $s, events_scale: 20}"
done
```

Every job carries an `events_strategy` label (`query-comment` in `dbt_project.yml`), so
`scripts/jobs_by_strategy.sql` groups bytes billed, slot-ms and duration per strategy.
`events_scale` multiplies thelook's events (same dates, more rows) so the differences show.
Mention the scaling in the post. Check `total_bytes_processed` of the full refresh before you
go above 20.

## 5. Execution: threads and the DAG

```bash
$DBT build --threads 1 && make gantt
$DBT build --threads 4 && make gantt
```

## 6. Airflow: the same manifest, now as tasks

```bash
make up    # parses first, so Cosmos finds dbt/target/manifest.json
```

- `thelook_dbt_single_task`: one `dbt build` task, the before picture.
- `thelook_dbt`: one task group per model with its tests, rendered from the manifest
  (`LoadMode.DBT_MANIFEST`), so the scheduler never runs dbt to parse the DAG.
- Retry demo: break `fct_orders.sql` (e.g. a typo in a column), trigger `thelook_dbt`, fix it,
  then clear only the failed task in the UI. Upstream models aren't rerun.
