select
    order_id,
    user_id,
    status,
    created_at,
    shipped_at,
    delivered_at
from {{ source('thelook', 'orders') }}
