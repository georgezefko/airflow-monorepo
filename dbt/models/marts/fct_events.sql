-- The experiment subject. Same model, four strategies:
--   dbt run -s fct_events --vars '{events_strategy: merge}'
--   merge_predicates | insert_overwrite_dynamic | insert_overwrite_static
-- Each run's jobs carry an events_strategy label (see dbt_project.yml query-comment).
{%- set strategy = var('events_strategy', 'merge') -%}
{%- set lookback = var('events_lookback_days', 3) | int -%}
{%- set recent_partitions = [] -%}
{%- for i in range(lookback + 1) -%}
    {%- do recent_partitions.append('date_sub(current_date(), interval ' ~ i ~ ' day)') -%}
{%- endfor %}

{{
    config(
        materialized='incremental',
        incremental_strategy='merge' if strategy.startswith('merge') else 'insert_overwrite',
        unique_key='event_id',
        incremental_predicates=(
            ['DBT_INTERNAL_DEST.event_date >= date_sub(current_date(), interval ' ~ lookback ~ ' day)']
            if strategy == 'merge_predicates' else none
        ),
        partitions=recent_partitions if strategy == 'insert_overwrite_static' else none,
        partition_by={'field': 'event_date', 'data_type': 'date'},
        cluster_by=['event_type'],
        on_schema_change='append_new_columns'
    )
}}

select
    event_id,
    session_id,
    user_id,
    sequence_number,
    event_type,
    traffic_source,
    browser,
    uri,
    created_at,
    date(created_at) as event_date
from {{ ref('int_events_scaled') }}
{% if is_incremental() %}
    -- Fixed window (not max(event_date) from target) so every strategy processes the same rows.
    where date(created_at) between date_sub(current_date(), interval {{ lookback }} day) and current_date()
{% endif %}
