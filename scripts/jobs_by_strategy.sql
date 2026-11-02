-- Demo 3 + 4: what dbt actually sent to BigQuery, and what it cost.
-- Run in the BigQuery console (same project, US region).
select
    creation_time,
    (select value from unnest(labels) where key = 'events_strategy') as strategy,
    statement_type,
    total_bytes_processed,
    total_bytes_billed,
    total_slot_ms,
    timestamp_diff(end_time, start_time, millisecond) as duration_ms,
    query
from `region-us`.INFORMATION_SCHEMA.JOBS
where
    creation_time > timestamp_sub(current_timestamp(), interval 1 day)
    and exists (
        select 1 from unnest(labels)
        where key = 'node_id' and value like '%fct_events%'
    )
order by creation_time
