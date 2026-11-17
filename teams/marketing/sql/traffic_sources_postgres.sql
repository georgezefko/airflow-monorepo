-- Postgres table for marketing_to_postgres; run before every load, so only "if not exists"
create schema if not exists marketing;
create table if not exists marketing.traffic_sources (
    traffic_source text primary key,
    orders bigint,
    customers bigint,
    orders_per_customer double precision,
    orders_share_pct double precision,
    orders_rank bigint
);
