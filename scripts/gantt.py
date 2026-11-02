"""Demo 5: ASCII Gantt of the last dbt run from target/run_results.json (stdlib only)."""

import json
import sys
from datetime import datetime
from pathlib import Path

WIDTH = 60


def rows(run_results: dict) -> list[tuple[str, str, datetime, datetime]]:
    out = []
    for r in run_results["results"]:
        execute = next((t for t in r["timing"] if t["name"] == "execute"), None)
        if execute and execute.get("started_at"):
            out.append(
                (
                    r["unique_id"].split(".")[-1],
                    r["thread_id"],
                    datetime.fromisoformat(execute["started_at"].rstrip("Z")),
                    datetime.fromisoformat(execute["completed_at"].rstrip("Z")),
                )
            )
    return sorted(out, key=lambda row: row[2])


def render(data: list[tuple[str, str, datetime, datetime]]) -> str:
    t0, t1 = min(r[2] for r in data), max(r[3] for r in data)
    span = (t1 - t0).total_seconds() or 1
    lines = []
    for name, thread, start, end in data:
        a = int((start - t0).total_seconds() / span * WIDTH)
        b = max(a + 1, int((end - t0).total_seconds() / span * WIDTH))
        lines.append(f"{name[:28]:28} {thread.split()[0]:>9} |{' ' * a}{'#' * (b - a)}")
    lines.append(f"{'':38} total {span:.1f}s")
    return "\n".join(lines)


if __name__ == "__main__":
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "dbt/target/run_results.json")
    print(render(rows(json.loads(path.read_text()))))
