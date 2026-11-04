select
    id as user_id,
    traffic_source,
    country,
    created_at
from {{ source('thelook', 'users') }}