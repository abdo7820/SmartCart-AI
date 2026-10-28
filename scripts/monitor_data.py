"""Compare reference/current tabular data and persist a local drift report."""

import argparse
import json
from pathlib import Path
import sys
import sqlite3
import re

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from smartcart import config  # noqa: E402
from smartcart.monitoring.data_quality import compare_frames  # noqa: E402
from smartcart.monitoring.store import MonitoringStore  # noqa: E402


def read_table(path):
    path = Path(path)
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def read_sqlite_table(path, table):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
        raise ValueError("table must be a simple SQLite table name")
    with sqlite3.connect(path) as connection:
        return pd.read_sql_query(f'SELECT * FROM "{table}"', connection)


def main():
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--reference", help="reference CSV or Parquet file")
    source.add_argument("--reference-db", help="reference SQLite database")
    parser.add_argument("--current", help="current CSV or Parquet file")
    parser.add_argument("--current-db", help="current SQLite database")
    parser.add_argument("--table", help="table to read from both SQLite databases")
    parser.add_argument("--name", default="dataset")
    parser.add_argument("--threshold", type=float, default=config.MONITOR_DRIFT_WARN)
    args = parser.parse_args()
    if args.reference_db or args.current_db:
        if not args.reference_db or not args.current_db or not args.table:
            parser.error("--reference-db, --current-db, and --table must be supplied together")
        reference, current = read_sqlite_table(args.reference_db, args.table), read_sqlite_table(args.current_db, args.table)
    else:
        if not args.reference or not args.current:
            parser.error("--reference and --current must be supplied together")
        reference, current = read_table(args.reference), read_table(args.current)
    report = compare_frames(reference, current, args.threshold)
    store = MonitoringStore(config.MONITORING_DB_PATH)
    try:
        store.record_drift(args.name, report)
    finally:
        store.close()
    print(json.dumps(report, indent=2))
    return 0 if report["status"] in ("ok", "unavailable") else 1


if __name__ == "__main__":
    raise SystemExit(main())
