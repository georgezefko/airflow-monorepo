select
    id as order_item_id,
    order_id,
    status,
    sale_price,
    created_at
from {{ source('thelook', 'order_items') }}