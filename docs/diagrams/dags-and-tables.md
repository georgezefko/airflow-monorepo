# DAGs and tables

Each team's DAG builds its own BigQuery dataset. `platform_dbt` builds staging, then updates the
`analytics_staging_ready` asset, which starts the team DAGs. Solid arrows are dbt `ref()`s.

```mermaid
flowchart LR
    subgraph src["thelook (public BigQuery)"]
        s_orders[(orders)]
        s_items[(order_items)]
        s_users[(users)]
        s_events[(events)]
    end

    subgraph platform["platform_dbt · @daily · dev_staging"]
        stg_orders["stg_orders (view)"]
        stg_items["stg_order_items (view)"]
        stg_users["stg_users (view)"]
        stg_events["stg_events (table, partitioned)"]
        ready{{staging_ready}}
    end

    subgraph sales["sales_dbt · dev_sales"]
        daily_orders["daily_orders (table)"]
        daily_revenue["daily_revenue (table)"]
    end

    subgraph marketing["marketing_dbt · dev_marketing"]
        int_events["int_events_scaled (view)"]
        fct_events["fct_events (incremental)"]
        by_source["orders_by_traffic_source (table)"]
    end

    s_orders --> stg_orders
    s_items --> stg_items
    s_users --> stg_users
    s_events --> stg_events

    stg_orders & stg_items & stg_users & stg_events --> ready
    ready -. "Asset: analytics_staging_ready" .-> sales & marketing

    stg_orders --> daily_orders
    stg_items --> daily_revenue
    stg_orders --> by_source
    stg_users --> by_source
    stg_events --> int_events --> fct_events
```
