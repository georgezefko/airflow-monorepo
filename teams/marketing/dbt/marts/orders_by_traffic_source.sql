select
    u.traffic_source,
    count(*) as orders,
    count(distinct o.user_id) as customers,
    round(count(*) / count(distinct o.user_id), 2) as orders_per_customer
from {{ ref('stg_orders') }} as o
join {{ ref('stg_users') }} as u using (user_id)
group by u.traffic_source
