import joblib
import numpy as np
import pandas as pd
import time

from . import config, db

FEATURE_TEXT = {
    "n_events": "total interactions", "n_views": "product views", "n_carts": "add-to-cart events",
    "n_purchases": "items purchased", "n_orders": "orders placed", "n_items": "distinct products seen",
    "n_items_bought": "distinct products bought", "n_sessions": "visits (sessions)", "active_days": "active days",
    "events_per_session": "interactions per visit", "days_since_last_event": "days since last activity",
    "days_since_last_purchase": "days since last purchase", "tenure_days": "days since first activity",
    "days_first_to_last_purchase": "days between first and last purchase", "ev_last7": "interactions in last 7 days",
    "ev_last30": "interactions in last 30 days", "purchases_last30": "purchases in last 30 days",
    "carts_last30": "add-to-carts in last 30 days", "recent_share": "share of activity in last 30 days",
    "trend_7_vs_30": "last-7-day vs last-30-day activity", "view_to_purchase": "views per purchase",
    "cart_rate": "cart rate (carts per view)", "purchase_rate": "purchase rate (purchases per interaction)",
}
CODES = {"view": 0, "addtocart": 1, "transaction": 2}


def build_features(events, cutoff):
    d = events[events["ts"] < cutoff].copy()
    d["code"] = d["event_type"].map(CODES).astype("int8")
    d = d.sort_values(["visitor_id", "ts"], kind="stable").reset_index(drop=True)
    if d.empty:
        return pd.DataFrame()
    f = d.groupby("visitor_id").agg(n_events=("ts", "size"), first_ts=("ts", "min"), last_ts=("ts", "max"), n_items=("item_id", "nunique"))
    cnt = d.groupby(["visitor_id", "code"]).size().unstack(fill_value=0).reindex(columns=[0, 1, 2], fill_value=0)
    f["n_views"], f["n_carts"], f["n_purchases"] = cnt[0], cnt[1], cnt[2]
    p = d[d["code"] == 2]
    g = p.groupby("visitor_id")
    f["last_purchase_ts"], f["first_purchase_ts"] = g["ts"].max(), g["ts"].min()
    f["n_items_bought"] = g["item_id"].nunique()
    f["n_orders"] = g["order_id"].nunique()
    for w in (7, 30):
        f[f"ev_last{w}"] = d[d["ts"] >= cutoff - w * config.DAY_MS].groupby("visitor_id").size()
    recent = d[d["ts"] >= cutoff - 30 * config.DAY_MS]
    f["purchases_last30"] = recent[recent["code"] == 2].groupby("visitor_id").size()
    f["carts_last30"] = recent[recent["code"] == 1].groupby("visitor_id").size()
    f["active_days"] = (d["ts"] // config.DAY_MS).groupby(d["visitor_id"]).nunique()
    gap = d.groupby("visitor_id")["ts"].diff()
    f["n_sessions"] = (gap.isna() | (gap > config.SESSION_GAP_MS)).groupby(d["visitor_id"]).sum()
    f = f.fillna({k: 0 for k in ["n_items_bought", "n_orders", "ev_last7", "ev_last30", "purchases_last30", "carts_last30"]})
    f["events_per_session"] = f["n_events"] / f["n_sessions"].clip(lower=1)
    f["days_since_last_event"] = ((cutoff - f["last_ts"]) / config.DAY_MS).clip(lower=0)
    f["tenure_days"] = ((cutoff - f["first_ts"]) / config.DAY_MS).clip(lower=0)
    f["days_since_last_purchase"] = ((cutoff - f["last_purchase_ts"]) / config.DAY_MS).clip(lower=0).fillna(f["tenure_days"] + 1)
    f["days_first_to_last_purchase"] = ((f["last_purchase_ts"] - f["first_purchase_ts"]) / config.DAY_MS).fillna(0)
    f["recent_share"] = f["ev_last30"] / f["n_events"]
    f["trend_7_vs_30"] = f["ev_last7"] / (f["ev_last30"] + 1)
    f["view_to_purchase"] = f["n_views"] / f["n_purchases"].clip(lower=1)
    f["cart_rate"] = f["n_carts"] / (f["n_views"] + 1)
    f["purchase_rate"] = f["n_purchases"] / f["n_events"]
    f = f.drop(columns=["first_ts", "last_ts", "last_purchase_ts", "first_purchase_ts"])
    return f.reset_index()


class ChurnService:
    def __init__(self, models_dir=None, monitor=None):
        models_dir = models_dir or config.MODELS_DIR
        self.monitor = monitor
        bundle = joblib.load(models_dir / "churn_all_models_bundle.joblib")
        self.name = bundle["selected_model_name"]
        self.calibrated = bundle["selected_calibrated_model"]
        self.raw = bundle["selected_raw_model"]
        self.features = list(bundle["features"])
        self.threshold = float(bundle["threshold"])
        self.low_cut = float(bundle["low_cut"])
        self.actions = bundle["actions"]
        self.definition = bundle["definition"]
        self.high_cut = self.threshold

    def tier_of(self, p):
        return np.where(p >= self.high_cut, "High", np.where(p >= self.low_cut, "Medium", "Low"))

    def contributions(self, X):
        if self.name == "logreg":
            return self.raw[:-1].transform(X) * self.raw[-1].coef_[0]
        if self.name == "lightgbm":
            return self.raw.booster_.predict(X, pred_contrib=True)[:, :-1]
        return None

    def score(self, events, cutoff, top_k=3):
        started = time.perf_counter()
        try:
            result = self._score(events, cutoff, top_k)
            summary = {"tier_counts": {tier: sum(1 for item in result if item["tier"] == tier) for tier in ("High", "Medium", "Low")}}
            if self.monitor:
                self.monitor.record_prediction(self.name, self.name, (time.perf_counter() - started) * 1000, True, summary)
            return result
        except Exception as exc:
            if self.monitor:
                self.monitor.record_prediction(self.name, self.name, (time.perf_counter() - started) * 1000, False, error_code=type(exc).__name__)
            raise

    def _score(self, events, cutoff, top_k=3):
        feats = build_features(events, cutoff)
        if feats.empty:
            return []
        feats = feats[feats["n_purchases"] > 0].reset_index(drop=True)
        if feats.empty:
            return []
        X = feats[self.features]
        p = self.calibrated.predict_proba(X)[:, 1]
        tiers = self.tier_of(p)
        contrib = self.contributions(X)
        out = []
        for r in range(len(X)):
            reasons = []
            if contrib is not None:
                for j in np.argsort(-np.abs(contrib[r]))[:top_k]:
                    reasons.append({"feature": self.features[j], "label": FEATURE_TEXT.get(self.features[j], self.features[j]),
                                    "value": float(X.iloc[r, j]), "effect": "raises risk" if contrib[r, j] > 0 else "lowers risk"})
            out.append({"visitor_id": int(feats.loc[r, "visitor_id"]), "churn_probability": float(p[r]), "tier": str(tiers[r]),
                        "action": self.actions[str(tiers[r])], "reasons": reasons})
        return out
