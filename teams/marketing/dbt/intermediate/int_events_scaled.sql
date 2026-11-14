{{ config(materialized='view') }}

select
    events.* replace (concat(events.event_id, '-', copy_n) as event_id)
from {{ ref('stg_events') }} as events
cross join unnest(generate_array(1, {{ var('events_scale', 1) }})) as copy_n