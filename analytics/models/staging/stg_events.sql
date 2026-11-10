{{
    config(
        materialized='table',
        partition_by={'field': 'created_at', 'data_type': 'timestamp', 'granularity': 'day'}
    )
}}

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
from {{ source('thelook', 'events' }}