with order_stats as (
    select
        user_id,
        min(created_at) as first_order_at,
        count(*) as lifetime_orders,
        sum(revenue) as lifetime_revenue
    from {{ ref('fct_orders') }}
    group by user_id
)

select
    users.user_id,
    users.age,
    users.gender,
    users.country,
    users.city,
    users.traffic_source,
    users.created_at,
    order_stats.first_order_at,
    coalesce(order_stats.lifetime_orders, 0) as lifetime_orders,
    coalesce(order_stats.lifetime_revenue, 0) as lifetime_revenue
from {{ ref('stg_users') }} as users
left join order_stats
    on users.user_id = order_stats.user_id
