select
    cast(id as string) as event_id,
    session_id,
    user_id,
    sequence_number,
    event_type,
    traffic_source,
    browser,
    uri,
    created_at
from {{ source('thelook', 'events') }}