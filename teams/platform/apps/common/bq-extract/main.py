"""Run a BigQuery query and write the result to a parquet file (gs:// or local).

  bq-extract --sql "select ..." --out gs://<bucket>/<dag>/<run>/extract.parquet

The query comes from the team's DAG, so a team changes what it extracts without a new image.
Credentials: Application Default Credentials. The project: GCP_PROJECT.
"""
import argparse
import os

import pyarrow.parquet as pq
from google.cloud import bigquery

p = argparse.ArgumentParser()
p.add_argument("--sql", required=True)
p.add_argument("--out", required=True)
args = p.parse_args()

table = bigquery.Client(project=os.environ["GCP_PROJECT"]).query(args.sql).to_arrow(create_bqstorage_client=False)
pq.write_table(table, args.out)  # pyarrow resolves gs:// with the same default credentials
print(f"{table.num_rows} rows -> {args.out}")
