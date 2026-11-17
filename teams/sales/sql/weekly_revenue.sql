-- Extract for sales_to_postgres: every week of analytics_sales.weekly_revenue
select week_start, revenue
from analytics_sales.weekly_revenue
order by week_start
