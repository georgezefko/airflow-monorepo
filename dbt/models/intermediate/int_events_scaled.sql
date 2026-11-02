-- thelook is too small for cost differences to show. This multiplies events by `events_scale`
-- (same dates, more rows per partition). Default 1 = passthrough. Say so in the post.
select
    events.* replace (concat(events.event_id, '-', copy_n) as event_id)  -- noqa: AM04
from {{ ref('stg_events') }} as events
cross join unnest(generate_array(1, {{ var('events_scale', 1) }})) as copy_n
