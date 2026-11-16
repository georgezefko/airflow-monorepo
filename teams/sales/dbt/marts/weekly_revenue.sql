select
    date_trunc(order_date, week(monday)) as week_start,
    sum(revenue) as revenue
from {{ ref('daily_revenue') }}
group by week_start
