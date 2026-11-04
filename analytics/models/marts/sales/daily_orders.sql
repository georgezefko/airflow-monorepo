{{ config(materialized='table') }}

select
    date(created_at) as order_date,
    count(*) as orders,
    countif(status = 'Cancelled') as cancelled_orders
from {{ ref('stg_orders') }}
group by order_date
