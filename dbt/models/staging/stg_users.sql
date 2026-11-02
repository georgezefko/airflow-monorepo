-- PII (names, email, address) deliberately left out
select
    id as user_id,
    age,
    gender,
    country,
    city,
    traffic_source,
    created_at
from {{ source('thelook', 'users') }}
