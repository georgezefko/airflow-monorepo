with items as (
    select
        order_id,
        sum(sale_price) as revenue,
        sum(margin) as margin
    from {{ ref('int_order_items_enriched') }}
    group by order_id
)

select
    orders.order_id,
    orders.user_id,
    orders.status,
    orders.item_count,
    orders.created_at,
    items.revenue,
    items.margin,
    date(orders.created_at) as order_date
from {{ ref('stg_orders') }} as orders
left join items
    on orders.order_id = items.order_id
