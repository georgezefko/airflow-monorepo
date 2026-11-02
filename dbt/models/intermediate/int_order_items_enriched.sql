select
    items.order_item_id,
    items.order_id,
    items.user_id,
    items.product_id,
    items.status,
    items.sale_price,
    items.created_at,
    products.category,
    products.brand,
    products.department,
    items.sale_price - products.cost as margin
from {{ ref('stg_order_items') }} as items
left join {{ ref('stg_products') }} as products
    on items.product_id = products.product_id
