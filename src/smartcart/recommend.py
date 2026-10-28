from collections import defaultdict

from . import config, db


def _rrf(rank_lists, weights):
    scores = defaultdict(float)
    for name, items in rank_lists.items():
        for r, item in enumerate(items, start=1):
            scores[item] += weights[name] / (config.RRF_K + r)
    return scores


def _neighbors(con, items, limit):
    if not items:
        return []
    marks = ",".join("?" * len(items))
    rows = con.execute(f"SELECT neighbor_id, SUM(score) AS s FROM item_neighbors WHERE item_id IN ({marks}) GROUP BY neighbor_id ORDER BY s DESC, neighbor_id LIMIT ?",
                       [*items, limit]).fetchall()
    return [int(r[0]) for r in rows]


def popular(con, limit):
    return [int(r[0]) for r in con.execute("SELECT item_id FROM item_popularity ORDER BY score DESC, item_id LIMIT ?", (limit,)).fetchall()]


def recommend(con, visitor_id, k=10, in_stock_only=False, exclude_bought=True, pool=200):
    hist = db.query(con, "SELECT item_id, event_type, session_id, ts FROM events WHERE visitor_id = ? ORDER BY ts, event_id", (visitor_id,))
    return hybrid(con, hist, k, in_stock_only, exclude_bought, pool)


def hybrid(con, hist, k=10, in_stock_only=False, exclude_bought=True, pool=200):
    seen = {int(r["item_id"]) for r in hist}
    bought = {int(r["item_id"]) for r in hist if r["event_type"] == "transaction"}
    if hist:
        last_session = hist[-1]["session_id"]
        ctx_items = list(dict.fromkeys(int(r["item_id"]) for r in reversed(hist) if r["session_id"] == last_session))[:10]
        w = {"view": 1.0, "addtocart": 3.0, "transaction": 5.0}
        strength = defaultdict(float)
        for r in hist:
            strength[int(r["item_id"])] += w[r["event_type"]]
        cf_items = [i for i, _ in sorted(strength.items(), key=lambda x: -x[1])[:20]]
    else:
        ctx_items, cf_items = [], []
    lists = {"ctx": _neighbors(con, ctx_items, pool), "cf": _neighbors(con, cf_items, pool), "pop": popular(con, pool)}
    scores = _rrf(lists, config.HYBRID_WEIGHTS)
    ranked = [i for i, _ in sorted(scores.items(), key=lambda x: -x[1])]
    if exclude_bought:
        ranked = [i for i in ranked if i not in bought]
    if not ranked:
        return [], "cold_start" if not hist else "no_candidates"
    marks = ",".join("?" * len(ranked))
    info = {r["item_id"]: r for r in db.query(con, f"SELECT item_id, name, brand, department, price, currency, in_stock, is_deal FROM products WHERE item_id IN ({marks})", ranked)}
    out = []
    for i in ranked:
        p = info.get(i)
        if p is None or (in_stock_only and p["in_stock"] != 1):
            continue
        sources = [n for n, items in lists.items() if i in set(items[:50])]
        out.append({**p, "score": round(scores[i], 6), "sources": sources, "already_viewed": i in seen})
        if len(out) >= k:
            break
    return out, "personalised" if hist else "cold_start"


def ranked_items(con, svc, hist, task, k=10, stock="any", exclude_bought=True):
    """stock: 'any', 'in_stock' (only known in stock) or 'not_out' (drop only items known to be out of stock)."""
    pool, _ = svc.rank(hist, task, k=0)
    mode = "personalised" if len(hist) else "cold_start"
    if pool is None or len(pool) == 0:
        return [], mode
    if task == "discovery":
        drop = set(hist["item_id"].astype("int64"))
    elif exclude_bought:
        drop = set(hist.loc[hist["event_type"] == "transaction", "item_id"].astype("int64"))
    else:
        drop = set()
    pool = pool[~pool["item"].isin(drop)]
    if len(pool) == 0:
        return [], mode
    ids = [int(i) for i in pool["item"].head(max(k * 6, 60)).tolist()]
    marks = ",".join("?" * len(ids))
    info = {r["item_id"]: r for r in db.query(con, f"SELECT item_id, name, brand, department, price, currency, in_stock, is_deal FROM products WHERE item_id IN ({marks})", ids)}
    out = []
    for _, row in pool.head(len(ids)).iterrows():
        p = info.get(int(row["item"]))
        if p is None:
            continue
        if stock == "in_stock" and p["in_stock"] != 1:
            continue
        if stock == "not_out" and p["in_stock"] == 0:
            continue
        sources = [n for n in ("ctx", "cf", "pop", "catpop") if row[f"rr_{n}"] > 0]
        out.append({**p, "score": round(float(row["model_score"]), 6), "sources": sources, "already_viewed": bool(row["p_decay"] > 0)})
        if len(out) >= k:
            break
    return out, mode


def recommend_ranked(con, svc, visitor_id, task, k=10, in_stock_only=False, exclude_bought=True):
    hist = db.frame(con, "SELECT ts, item_id, event_type, session_id FROM events WHERE visitor_id = ? ORDER BY ts, event_id", (visitor_id,))
    return ranked_items(con, svc, hist, task, k, "in_stock" if in_stock_only else "any", exclude_bought)
