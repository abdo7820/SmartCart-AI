import argparse
import re
import sqlite3
import sys
import time
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
CORE_ORDER = ["db_info", "categories", "products", "customers", "customer_features", "sessions", "orders", "order_items", "cart_items", "events", "daily_stats"]
TYPE_MAP = {"INTEGER": "BIGINT", "REAL": "DOUBLE PRECISION", "TEXT": "TEXT", "": "TEXT"}


def translate_schema(sql):
    sql = re.sub(r"\bINTEGER\b", "BIGINT", sql)
    sql = re.sub(r"\bREAL\b", "DOUBLE PRECISION", sql)
    sql = sql.replace("datetime(e.ts / 1000, 'unixepoch')", "to_char(to_timestamp(e.ts / 1000.0) AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')")
    return sql


def split_schema(sql):
    views_at = sql.index("CREATE VIEW")
    idx_at = sql.index("CREATE INDEX")
    return sql[:idx_at], sql[idx_at:views_at], sql[views_at:]


def extra_tables(lite):
    core = set(CORE_ORDER)
    rows = lite.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall()
    return [r[0] for r in rows if r[0] not in core]


def create_extra(pg, lite, name):
    cols = lite.execute(f"PRAGMA table_info({name})").fetchall()
    defs = ", ".join(f'"{c[1]}" {TYPE_MAP.get(c[2].upper(), "TEXT")}' for c in cols)
    pg.execute(f'DROP TABLE IF EXISTS "{name}" CASCADE')
    pg.execute(f'CREATE TABLE "{name}" ({defs})')


def copy_table(pg, lite, name, chunk=200_000):
    cols = [c[1] for c in lite.execute(f"PRAGMA table_info({name})").fetchall()]
    col_list = ", ".join(f'"{c}"' for c in cols)
    cur = lite.execute(f"SELECT {col_list} FROM {name}")
    n = 0
    with pg.cursor() as c, c.copy(f'COPY "{name}" ({col_list}) FROM STDIN') as cp:
        while True:
            rows = cur.fetchmany(chunk)
            if not rows:
                break
            for r in rows:
                cp.write_row(r)
            n += len(rows)
    return n


def main(sqlite_path, url, schema_path):
    lite = sqlite3.connect(sqlite_path)
    schema = translate_schema(Path(schema_path).read_text())
    tables_sql, index_sql, views_sql = split_schema(schema)
    t0 = time.time()
    with psycopg.connect(url, autocommit=True) as pg:
        for name in reversed(CORE_ORDER):
            pg.execute(f'DROP TABLE IF EXISTS "{name}" CASCADE')
        pg.execute(tables_sql)
        extras = extra_tables(lite)
        for name in extras:
            create_extra(pg, lite, name)
        for name in CORE_ORDER + extras:
            t = time.time()
            n = copy_table(pg, lite, name)
            print(f"{name:20s} {n:>10,} rows  [{time.time() - t:.1f}s]", flush=True)
        pg.execute(index_sql)
        pg.execute(views_sql)
        pg.execute("CREATE INDEX IF NOT EXISTS idx_neighbors_item ON item_neighbors(item_id, score DESC)") if "item_neighbors" in extras else None
        pg.execute("CREATE INDEX IF NOT EXISTS idx_rk_item ON rk_item_features(item_id)") if "rk_item_features" in extras else None
        pg.execute("CREATE INDEX IF NOT EXISTS idx_rk_cat ON rk_category_top(category_id)") if "rk_category_top" in extras else None
        pg.execute("ANALYZE")
        print(f"migrated in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqlite", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--schema", default=str(ROOT / "data" / "db" / "schema.sql"))
    a = ap.parse_args()
    main(a.sqlite, a.url, a.schema)
