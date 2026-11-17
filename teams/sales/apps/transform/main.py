"""Sales' transform: weekly revenue plus its change on the week before.

  transform --in <extract.parquet> --out <transform.parquet>   (gs:// or local paths)
"""
import argparse

import pyarrow as pa
import pyarrow.parquet as pq

p = argparse.ArgumentParser()
p.add_argument("--in", dest="src", required=True)
p.add_argument("--out", required=True)
args = p.parse_args()

df = pq.read_table(args.src).to_pandas().sort_values("week_start")
df["revenue_change_pct"] = (df["revenue"].pct_change() * 100).round(1)
pq.write_table(pa.Table.from_pandas(df, preserve_index=False), args.out)
print(f"{len(df)} weeks -> {args.out}")
