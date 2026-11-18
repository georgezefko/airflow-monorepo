"""Marketing's transform: each traffic source's share of all orders, and its rank.

  transform --in <extract.parquet> --out <transform.parquet>   (gs:// or local paths)
"""
import argparse

import pyarrow as pa
import pyarrow.parquet as pq

p = argparse.ArgumentParser()
p.add_argument("--in", dest="src", required=True)
p.add_argument("--out", required=True)
args = p.parse_args()

df = pq.read_table(args.src).to_pandas()
df["orders_share_pct"] = (df["orders"] / df["orders"].sum() * 100).round(1)
df["orders_rank"] = df["orders"].rank(ascending=False, method="min").astype("int64")
df = df.sort_values("orders_rank")
pq.write_table(pa.Table.from_pandas(df, preserve_index=False), args.out)
print(f"{len(df)} traffic sources -> {args.out}")
