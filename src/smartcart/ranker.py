import json

import joblib
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

from . import config, db

DAY_MS = config.DAY_MS
SRC = ["ctx", "cf", "pop", "catpop"]
CODES = {"view": 0, "addtocart": 1, "transaction": 2}
W = np.array([config.EVENT_WEIGHTS["view"], config.EVENT_WEIGHTS["addtocart"], config.EVENT_WEIGHTS["transaction"]])
GROUPED = {"XGBoost Ranker", "LightGBM Ranker"}
ITEM_COLS = ["i_views", "i_carts", "i_buys", "i_users", "i_days_since_last", "i_buy_rate", "i_cart_rate", "i_age_days", "i_pop_7d", "i_pop_30d", "i_trend"]
TABLES = ["rk_item_features", "rk_catalog", "rk_sim", "rk_category_share", "rk_category_top", "rk_pop_top"]


def available(con):
    have = con.tables()
    return all(t in have for t in TABLES + ["rk_meta"])


def _empty():
    return pd.DataFrame({"item": np.array([], dtype="int64"), "rank": np.array([], dtype="int64"), "score": np.array([], dtype="float64")})


def _rank_top(frame, n):
    frame = frame.sort_values("score", ascending=False, kind="stable").copy()
    frame["rank"] = np.arange(1, len(frame) + 1)
    return frame[frame["rank"] <= n][["item", "rank", "score"]].reset_index(drop=True)


class RankerService:
    def __init__(self, tables, item_cat, as_of, models_dir=None):
        models_dir = models_dir or config.MODELS_DIR
        self.cfg = json.loads((models_dir / "recommendation_config.json").read_text())
        self.models = {}
        for task in ("purchase", "discovery"):
            name = self.cfg[task]["final_model"]
            fname = f"{task}_{name.replace(' ', '_')}.joblib"
            self.models[task] = (name, joblib.load(models_dir / "models" / fname))
        self.items = tables["rk_item_features"].set_index("item_id")
        self.catalog = tables["rk_catalog"]["item_id"].to_numpy("int64")
        self.c_index = pd.Index(self.catalog)
        sim = tables["rk_sim"]
        r = self.c_index.get_indexer(sim["item_id"])
        c = self.c_index.get_indexer(sim["neighbor_id"])
        ok = (r >= 0) & (c >= 0)
        self.sim = csr_matrix((sim["sim"].to_numpy("float32")[ok], (r[ok], c[ok])), shape=(len(self.catalog), len(self.catalog)))
        cs = tables["rk_category_share"]
        self.cat_share = pd.Series(cs["share"].to_numpy(), index=cs["category_id"].to_numpy("int64"))
        self.cat_items = tables["rk_category_top"].rename(columns={"category_id": "cat", "item_id": "item"})
        pt = tables["rk_pop_top"].sort_values("score", ascending=False, kind="stable")
        self.pop_top = pd.Series(pt["score"].to_numpy(), index=pt["item_id"].to_numpy("int64"))
        self.item_cat = item_cat
        self.as_of = int(as_of)

    @classmethod
    def from_db(cls, con, models_dir=None):
        tables = {t: db.frame(con, f"SELECT * FROM {t}") for t in TABLES}
        cats = db.frame(con, "SELECT item_id, raw_category_id FROM products WHERE raw_category_id IS NOT NULL")
        item_cat = pd.Series(cats["raw_category_id"].to_numpy("int64"), index=cats["item_id"].to_numpy("int64"))
        as_of = int(con.execute("SELECT value FROM rk_meta WHERE key = 'as_of_ms'").fetchone()["value"])
        return cls(tables, item_cat, as_of, models_dir)

    def features_for(self, task):
        return list(self.cfg[task]["features"])

    def context(self, hist, session_id=None, cut_events=None):
        """hist: all events of one visitor (ts, item_id, event_type, session_id), sorted by ts."""
        if hist.empty:
            return None
        hist = hist.assign(code=hist["event_type"].map(CODES).astype("int8")).sort_values("ts", kind="stable").reset_index(drop=True)
        hist["w"] = W[hist["code"].to_numpy()]
        first_seen = int(hist["ts"].min())
        sid = hist["session_id"].iloc[-1] if session_id is None else session_id
        sess = hist[hist["session_id"] == sid]
        sess_start = int(sess["ts"].min())
        if cut_events is None:
            in_sess = sess.tail(config.CUT_EVENTS)
        else:
            in_sess = sess.head(cut_events)
        cut_ts = int(in_sess["ts"].iloc[-1])
        bought = set(hist.loc[(hist["code"] == 2) & (hist["ts"] < cut_ts), "item_id"].astype("int64"))
        lo = cut_ts - config.HISTORY_DAYS * DAY_MS
        past = hist[(hist["ts"] < sess_start) & (hist["ts"] >= lo)]
        ctx = pd.concat([past.assign(in_sess=0), in_sess.assign(in_sess=1)]).sort_values("ts", kind="stable").tail(config.MAX_CTX_EVENTS)
        ctx = ctx.rename(columns={"item_id": "item"})
        age = (cut_ts - ctx["ts"]) / DAY_MS
        ctx["decay"] = ctx["w"] * np.exp2(-age / config.HALF_LIFE_DAYS) * np.where(ctx["in_sess"] == 1, config.SESSION_BOOST, 1.0)
        ctx["is_view"], ctx["is_cart"], ctx["is_buy"] = ctx["code"] == 0, ctx["code"] == 1, ctx["code"] == 2
        qi = ctx.groupby("item", sort=False).agg(p_views=("is_view", "sum"), p_carts=("is_cart", "sum"), p_buys=("is_buy", "sum"),
                                                p_sess_events=("in_sess", "sum"), last_ts=("ts", "max"), p_decay=("decay", "sum")).reset_index()
        h, s = ctx[ctx["in_sess"] == 0], ctx[ctx["in_sess"] == 1]
        info = {
            "q_sess_items": float(s["item"].nunique()), "q_sess_carts": float(s["is_cart"].sum()), "q_hist_events": float(len(h)),
            "q_hist_items": float(h["item"].nunique()), "q_hist_buys": float(h["is_buy"].sum()),
            "q_days_since_prev": float((sess_start - h["ts"].max()) / DAY_MS) if len(h) else config.UNSEEN_DAYS,
            "warm": float(first_seen < sess_start),
        }
        t = pd.Timestamp(cut_ts, unit="ms", tz="UTC")
        info["q_hour"], info["q_dow"] = float(t.hour), float(t.dayofweek)
        last_item = int(s.sort_values("ts", kind="stable")["item"].iloc[-1])
        qi = qi[~qi["item"].isin(bought) & (qi["p_buys"] == 0)].reset_index(drop=True)
        return {"qi": qi, "info": info, "bought": bought, "cut_ts": cut_ts, "last_item": last_item}

    def _cold_context(self):
        t = pd.Timestamp(self.as_of, unit="ms", tz="UTC")
        info = {"q_sess_items": 0.0, "q_sess_carts": 0.0, "q_hist_events": 0.0, "q_hist_items": 0.0, "q_hist_buys": 0.0,
                "q_days_since_prev": config.UNSEEN_DAYS, "warm": 0.0, "q_hour": float(t.hour), "q_dow": float(t.dayofweek)}
        qi = pd.DataFrame({"item": np.array([], dtype="int64"), "p_views": [], "p_carts": [], "p_buys": [], "p_sess_events": [], "last_ts": [], "p_decay": []})
        return {"qi": qi, "info": info, "bought": set(), "cut_ts": self.as_of, "last_item": None}

    def sources(self, c, n=100):
        qi, bought = c["qi"], c["bought"]
        touched = set(qi["item"].astype("int64"))
        out = {"ctx": _rank_top(qi.rename(columns={"p_decay": "score"})[["item", "score"]], n) if len(qi) else _empty()}
        incat = qi[qi["item"].isin(self.c_index)]
        if len(incat):
            vec = np.zeros((1, len(self.c_index)), dtype="float32")
            vec[0, self.c_index.get_indexer(incat["item"])] = incat["p_decay"].to_numpy("float32")
            scores = (csr_matrix(vec) @ self.sim).toarray()[0]
            scores[self.c_index.get_indexer(incat["item"])] = -np.inf
            top = np.argsort(-scores, kind="stable")[:n]
            fr = pd.DataFrame({"item": self.catalog[top], "score": scores[top]})
            fr = fr[np.isfinite(fr["score"]) & (fr["score"] > 0) & ~fr["item"].isin(bought)]
            out["cf"] = _rank_top(fr, n) if len(fr) else _empty()
        else:
            out["cf"] = _empty()
        pop = pd.DataFrame({"item": self.pop_top.index.to_numpy(), "score": self.pop_top.to_numpy()})
        pop = pop[~pop["item"].isin(touched) & ~pop["item"].isin(bought)]
        out["pop"] = _rank_top(pop, n) if len(pop) else _empty()
        own = qi.assign(cat=qi["item"].map(self.item_cat)).dropna(subset=["cat"]).astype({"cat": "int64"})
        if len(own):
            wts = own.groupby("cat")["p_decay"].sum().reset_index()
            wts["share"] = wts["p_decay"] / wts["p_decay"].sum()
            wts = wts.sort_values("share", ascending=False, kind="stable").head(2)
            cand = wts.merge(self.cat_items, on="cat")
            cand["score"] = cand["share"] * cand["cscore"]
            cand = cand[~cand["item"].isin(touched) & ~cand["item"].isin(bought)][["item", "score"]]
            out["catpop"] = _rank_top(cand, n) if len(cand) else _empty()
        else:
            out["catpop"] = _empty()
        return out

    def pool(self, c, srcs):
        pool = None
        for name in SRC:
            top = srcs[name]
            top = top[top["rank"] <= config.N_PER_SOURCE]
            top = top.assign(**{f"rr_{name}": 1.0 / top["rank"], f"score_{name}": top["score"]}).drop(columns=["rank", "score"])
            pool = top if pool is None else pool.merge(top, on="item", how="outer")
        pool = pool.fillna(0.0)
        for name in SRC:
            if name != "pop":
                pool[f"score_{name}"] = pool[f"score_{name}"].clip(lower=0.0)
        rr = pool[[f"rr_{s}" for s in SRC]].to_numpy()
        pool["n_sources"] = (rr > 0).sum(axis=1)
        pool["rrf"] = np.where(rr > 0, 1.0 / (60.0 + 1.0 / np.where(rr > 0, rr, 1.0)), 0.0).sum(axis=1)
        if pool.empty:
            return pool
        for k, v in c["info"].items():
            pool[k] = v
        pool = pool.merge(self.items[ITEM_COLS].reset_index().rename(columns={"item_id": "item"}), on="item", how="left")
        pool["i_new"] = pool["i_views"].isna().astype("int8")
        qi = c["qi"]
        pool = pool.merge(qi[["item", "p_views", "p_carts", "p_sess_events", "p_decay", "last_ts"]], on="item", how="left")
        pool["p_days_since_last"] = ((c["cut_ts"] - pool["last_ts"]) / DAY_MS).fillna(config.UNSEEN_DAYS)
        pool["cat"] = pool["item"].map(self.item_cat)
        cc = qi.assign(cat=qi["item"].map(self.item_cat)).dropna(subset=["cat"])
        cc = cc.groupby("cat")["p_decay"].sum().rename("cat_w").reset_index()
        cc["p_cat_share"] = cc["cat_w"] / cc["cat_w"].sum() if len(cc) else []
        pool = pool.merge(cc[["cat", "p_cat_share"]], on="cat", how="left")
        pool["i_cat_share"] = pool["cat"].map(self.cat_share)
        last_cat = self.item_cat.get(c["last_item"]) if c["last_item"] is not None else None
        pool["p_same_cat_as_last"] = ((pool["cat"] == last_cat) & pool["cat"].notna() & (last_cat is not None)).astype("int8")
        zero = ITEM_COLS + ["p_views", "p_carts", "p_sess_events", "p_decay", "p_cat_share", "i_cat_share"]
        pool[zero] = pool[zero].fillna(0.0)
        return pool.drop(columns=["cat", "last_ts"])

    def rank(self, hist, task, k=10, session_id=None, cut_events=None):
        c = self.context(hist, session_id, cut_events) if len(hist) else None
        c = c if c is not None else self._cold_context()
        pool = self.pool(c, self.sources(c))
        if pool.empty:
            return pool, c
        if task == "discovery":
            pool = pool[pool["p_decay"] == 0].reset_index(drop=True)
            if pool.empty:
                return pool, c
        feats = self.features_for(task)
        name, model = self.models[task]
        X = pool[feats].astype("float32")
        pool = pool.assign(model_score=model.predict(X) if name in GROUPED else model.predict_proba(X)[:, 1])
        pool = pool.sort_values(["model_score", "rrf"], ascending=[False, False], kind="stable").reset_index(drop=True)
        return pool.head(k) if k else pool, c
