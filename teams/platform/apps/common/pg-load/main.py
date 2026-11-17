"""Load a parquet file (gs:// or local) into a Postgres table, replacing its rows.

  pg-load --in gs://.../transform.parquet --table sales.top_customers --ddl "create table if not exists ..."

Creates the database if it doesn't exist, then runs --ddl (the team's own create statements), then
replaces the table's rows in one transaction, so a rerun gives the same result.
Connection: the standard libpq variables PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE.
"""
import argparse
import os

import psycopg
import pyarrow.parquet as pq
from psycopg import sql

p = argparse.ArgumentParser()
p.add_argument("--in", dest="src", required=True)
p.add_argument("--table", required=True, help="schema.table")
p.add_argument("--ddl", default="", help="SQL run before loading, e.g. create table if not exists")
args = p.parse_args()

db = os.environ["PGDATABASE"]
# create database can't run in a transaction, and Postgres has no "if not exists" for it
with psycopg.connect(dbname="postgres", autocommit=True) as conn:
    if not conn.execute("select 1 from pg_database where datname = %s", [db]).fetchone():
        conn.execute(sql.SQL("create database {}").format(sql.Identifier(db)))

data = pq.read_table(args.src)
table = sql.Identifier(*args.table.split("."))
cols = sql.SQL(", ").join(map(sql.Identifier, data.column_names))
with psycopg.connect() as conn:  # one transaction: readers never see a half-loaded table
    if args.ddl:
        conn.execute(args.ddl)
    conn.execute(sql.SQL("delete from {}").format(table))
    with conn.cursor().copy(sql.SQL("copy {} ({}) from stdin").format(table, cols)) as copy:
        for row in zip(*(c.to_pylist() for c in data.columns)):
            copy.write_row(row)
print(f"{data.num_rows} rows -> {db}.{args.table}")
