select
    date(created_at) as order_date,
    sum(sale_price) as revenue
from {{ ref('stg_order_items') }}
where status not in ('Cancelled', 'Returned')
group by order_date
