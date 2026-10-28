import argparse
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from smartcart import ranker_state  # noqa: E402


def main(db_path, as_of=None):
    con = sqlite3.connect(db_path)
    t0 = time.time()
    ev = pd.read_sql_query("SELECT ts, visitor_id, item_id, event_type FROM events", con)
    S = int(as_of) if as_of else int(ev["ts"].max()) + 1
    cat = pd.read_sql_query("SELECT item_id, raw_category_id FROM products WHERE raw_category_id IS NOT NULL", con)
    item_cat = pd.Series(cat["raw_category_id"].to_numpy("int64"), index=cat["item_id"].to_numpy("int64"))
    state = ranker_state.build_state(ev, item_cat, S)
    for name, frame in state.items():
        con.execute(f"DROP TABLE IF EXISTS {name}")
        frame.to_sql(name, con, if_exists="replace", index=False, chunksize=200_000)
        print(f"{name:20s} {len(frame):>10,} rows")
    con.execute("CREATE INDEX IF NOT EXISTS idx_rk_item ON rk_item_features(item_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_rk_cat ON rk_category_top(category_id)")
    con.execute("DROP TABLE IF EXISTS rk_meta")
    con.execute("CREATE TABLE rk_meta (key TEXT PRIMARY KEY, value TEXT)")
    con.execute("INSERT INTO rk_meta VALUES ('as_of_ms', ?)", (str(S),))
    con.commit()
    con.close()
    print(f"done in {time.time() - t0:.1f}s | state as of {pd.Timestamp(S, unit='ms')}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--as-of", default=None)
    a = ap.parse_args()
    main(a.db, a.as_of)
