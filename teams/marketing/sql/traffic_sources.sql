-- Extract for marketing_to_postgres: orders and customers per traffic source
select traffic_source, orders, customers, orders_per_customer
from analytics_marketing.orders_by_traffic_source
