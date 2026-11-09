"""Run a .sql file of named DuckDB queries against the Stage 1 CSVs.

Each query starts with a line `-- name: <slug>`. Results go to outputs/phase2/<slug>.csv.
Usage: python src/p2_run_sql.py 00_validation.sql 01_business_queries.sql [--data DIR]   (files resolved in sql/)
"""
import argparse
import re
from pathlib import Path

import duckdb

from config import DATA, OUTPUTS, SQL

TABLES = ["orders", "user_churn_features", "daily_kpis", "brand_monthly_funnel",
          "category_monthly_funnel", "hour_dow_activity", "session_summary",
          "cohort_retention_visitors", "cohort_retention_buyers", "products",
          "data_quality_report"]


def connect(data_dir: Path) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for t in TABLES:
        con.sql(f"CREATE VIEW {t} AS SELECT * FROM read_csv_auto('{data_dir / (t + '.csv')}')")
    return con


def split_named(sql_text: str) -> list[tuple[str, str]]:
    """Split a file on `-- name:` markers into (slug, sql) pairs."""
    parts = re.split(r"^-- name:\s*(\S+)\s*$", sql_text, flags=re.M)
    return [(parts[i], parts[i + 1].strip().rstrip(";")) for i in range(1, len(parts), 2)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--data", default=str(DATA))
    args = ap.parse_args()
    con = connect(Path(args.data))
    out = OUTPUTS / "phase2"
    out.mkdir(parents=True, exist_ok=True)
    for f in args.files:
        for slug, sql in split_named((SQL / f).read_text()):
            df = con.sql(sql).df()
            df.to_csv(out / f"{slug}.csv", index=False)
            print(f"\n== {slug} ({len(df)} rows)\n{df.head(25).to_string(index=False)}")


if __name__ == "__main__":
    main()
