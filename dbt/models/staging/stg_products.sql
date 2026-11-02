select
    id as product_id,
    name as product_name,
    brand,
    category,
    department,
    cost,
    retail_price
from {{ source('thelook', 'products') }}
