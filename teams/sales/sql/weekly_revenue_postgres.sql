-- Postgres table for sales_to_postgres; run before every load, so only "if not exists"
create schema if not exists sales;
create table if not exists sales.weekly_revenue (
    week_start date primary key,
    revenue double precision,
    revenue_change_pct double precision
);
