import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.preprocessing import normalize

from . import config

DAY_MS = config.DAY_MS
CODES = {"view": 0, "addtocart": 1, "transaction": 2}
WEIGHTS = np.array([config.EVENT_WEIGHTS["view"], config.EVENT_WEIGHTS["addtocart"], config.EVENT_WEIGHTS["transaction"]])


def popularity_scores(ts, items, w, T, window_days):
    lo = np.searchsorted(ts, T - window_days * DAY_MS, "left")
    hi = np.searchsorted(ts, T, "left")
    return pd.Series(w[lo:hi]).groupby(items[lo:hi]).sum().sort_values(ascending=False, kind="stable")


def build_state(events, item_cat, S, sim_top=config.SIM_TOP_NEIGHBORS):
    events = events[events["ts"] < S].sort_values("ts", kind="stable")
    ts = events["ts"].to_numpy("int64")
    users = events["visitor_id"].to_numpy("int64")
    items = events["item_id"].to_numpy("int64")
    codes = events["event_type"].map(CODES).to_numpy("int8")
    w = WEIGHTS[codes]
    d = pd.DataFrame({"user": users, "item": items, "views": (codes == 0).astype("int32"), "carts": (codes == 1).astype("int32"),
                      "buys": (codes == 2).astype("int32"), "ts": ts})
    ui = d.groupby(["user", "item"], sort=False).agg(views=("views", "sum"), carts=("carts", "sum"), buys=("buys", "sum"),
                                                    first_ts=("ts", "min"), last_ts=("ts", "max")).reset_index()
    del d
    t = ui.groupby("item").agg(i_views=("views", "sum"), i_carts=("carts", "sum"), i_buys=("buys", "sum"), i_users=("user", "size"),
                               first_ts=("first_ts", "min"), last_ts=("last_ts", "max"))
    ev_total = t["i_views"] + t["i_carts"] + t["i_buys"]
    t["i_days_since_last"] = (S - t["last_ts"]) / DAY_MS
    t["i_age_days"] = (S - t["first_ts"]) / DAY_MS
    t["i_buy_rate"] = t["i_buys"] / ev_total
    t["i_cart_rate"] = t["i_carts"] / (t["i_views"] + 1)
    t["i_pop_7d"] = popularity_scores(ts, items, w, S, 7).reindex(t.index).fillna(0.0)
    t["i_pop_30d"] = popularity_scores(ts, items, w, S, 30).reindex(t.index).fillna(0.0)
    t["i_trend"] = t["i_pop_7d"] / (t["i_pop_30d"] + 1.0)
    item_table = t.drop(columns=["first_ts", "last_ts"])

    catalog = ev_total.nlargest(config.TOP_N_ITEMS).index.to_numpy()
    cu = ui[ui["item"].isin(catalog)]
    per_user = cu.groupby("user").size()
    cu = cu[cu["user"].isin(per_user[per_user <= config.MAX_USER_ITEMS].index)]
    m_users = pd.Index(cu["user"].unique())
    c_index = pd.Index(catalog)
    X = csr_matrix((np.ones(len(cu), dtype=np.float32), (m_users.get_indexer(cu["user"]), c_index.get_indexer(cu["item"]))),
                   shape=(len(m_users), len(c_index)))
    normed = normalize(X.T.tocsr(), norm="l2", axis=1)
    sim = (normed @ normed.T).tocsr()
    sim.setdiag(0)
    sim.eliminate_zeros()
    rows, cols, vals = [], [], []
    for r in range(sim.shape[0]):
        a, b = sim.indptr[r], sim.indptr[r + 1]
        if b == a:
            continue
        idx, v = sim.indices[a:b], sim.data[a:b]
        if len(v) > sim_top:
            top = np.argpartition(-v, sim_top - 1)[:sim_top]
            idx, v = idx[top], v[top]
        rows.append(np.full(len(v), catalog[r], dtype="int64"))
        cols.append(catalog[idx])
        vals.append(v)
    sim_table = pd.DataFrame({"item_id": np.concatenate(rows), "neighbor_id": np.concatenate(cols), "sim": np.concatenate(vals).astype("float64")})

    recent_lo = np.searchsorted(ts, S - 30 * DAY_MS, "left")
    recent_cat = pd.Series(items[recent_lo:]).map(item_cat).to_numpy()
    cw = pd.Series(w[recent_lo:]).groupby(recent_cat).sum()
    cat_share = (cw / cw.sum()).rename("share")

    pop7 = popularity_scores(ts, items, w, S, config.POP_WINDOW_DAYS)
    ci = pd.DataFrame({"item": pop7.index.to_numpy(), "pop": pop7.to_numpy()})
    ci["cat"] = ci["item"].map(item_cat)
    ci = ci.dropna(subset=["cat"]).astype({"cat": "int64"})
    ci["crank"] = ci.groupby("cat").cumcount() + 1
    ci = ci[ci["crank"] <= 100].copy()
    ci["cscore"] = ci["pop"] / ci.groupby("cat")["pop"].transform("max")
    pop_top = pop7.head(config.N_PER_SOURCE + 500)
    return {
        "rk_item_features": item_table.reset_index().rename(columns={"item": "item_id"}),
        "rk_catalog": pd.DataFrame({"item_id": catalog}),
        "rk_sim": sim_table,
        "rk_category_share": pd.DataFrame({"category_id": cat_share.index.astype("int64"), "share": cat_share.to_numpy()}),
        "rk_category_top": ci[["cat", "item", "cscore"]].rename(columns={"cat": "category_id", "item": "item_id"}),
        "rk_pop_top": pd.DataFrame({"item_id": pop_top.index.to_numpy(), "score": pop_top.to_numpy()}),
    }
