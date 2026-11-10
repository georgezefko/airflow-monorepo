select
    order_id,
    user_id,
    status,
    created_at
from {{ source('thelook', 'orders') }}
