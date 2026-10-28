import argparse
import sqlite3
import time

import numpy as np
import pandas as pd

MAX_ITEMS_PER_SESSION = 25
TOP_NEIGHBORS = 30


def main(db_path):
    con = sqlite3.connect(db_path)
    t0 = time.time()
    ev = pd.read_sql_query("SELECT session_id, item_id, event_type FROM events", con)
    w = ev["event_type"].map({"view": 1.0, "addtocart": 3.0, "transaction": 5.0})
    ev["w"] = w
    pairs_src = ev.groupby(["session_id", "item_id"], as_index=False)["w"].max()
    n_items = pairs_src.groupby("session_id")["item_id"].transform("size")
    pairs_src = pairs_src[(n_items >= 2) & (n_items <= MAX_ITEMS_PER_SESSION)]
    a = pairs_src.rename(columns={"item_id": "a", "w": "wa"})
    b = pairs_src.rename(columns={"item_id": "b", "w": "wb"})
    pr = a.merge(b, on="session_id")
    pr = pr[pr["a"] != pr["b"]]
    pr["s"] = np.minimum(pr["wa"], pr["wb"]) / np.log1p(pr.groupby("session_id")["a"].transform("nunique"))
    co = pr.groupby(["a", "b"], as_index=False)["s"].sum()
    pop = ev.groupby("item_id").size().rename("pop")
    co = co.join(pop, on="b")
    co["score"] = co["s"] / np.sqrt(co["pop"])
    co = co.sort_values(["a", "score"], ascending=[True, False])
    co = co.groupby("a").head(TOP_NEIGHBORS)[["a", "b", "score"]]
    co.columns = ["item_id", "neighbor_id", "score"]
    con.execute("DROP TABLE IF EXISTS item_neighbors")
    con.execute("CREATE TABLE item_neighbors (item_id INTEGER NOT NULL, neighbor_id INTEGER NOT NULL, score REAL NOT NULL, PRIMARY KEY (item_id, neighbor_id))")
    co.to_sql("item_neighbors", con, if_exists="append", index=False, chunksize=200_000)
    con.execute("CREATE INDEX IF NOT EXISTS idx_neighbors_item ON item_neighbors(item_id, score DESC)")
    con.execute("DROP TABLE IF EXISTS item_popularity")
    con.execute("CREATE TABLE item_popularity (item_id INTEGER PRIMARY KEY, score REAL NOT NULL)")
    ts_max = int(pd.read_sql_query("SELECT MAX(ts) AS m FROM events", con)["m"][0])
    recent = pd.read_sql_query(f"SELECT item_id, event_type FROM events WHERE ts >= {ts_max - 30 * 86_400_000}", con)
    recent["w"] = recent["event_type"].map({"view": 1.0, "addtocart": 3.0, "transaction": 5.0})
    popularity = recent.groupby("item_id")["w"].sum().rename("score").reset_index()
    popularity.to_sql("item_popularity", con, if_exists="append", index=False)
    con.commit()
    print(f"item_neighbors: {len(co):,} rows | item_popularity: {len(popularity):,} rows | {time.time() - t0:.1f}s")
    con.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    main(ap.parse_args().db)
