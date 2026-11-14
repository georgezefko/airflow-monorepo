select
    u.traffic_source,
    count(*) as orders,
    count(distinct o.user_id) as customers
from {{ ref('stg_orders') }} as o
join {{ ref('stg_users') }} as u using (user_id)
group by u.traffic_source
