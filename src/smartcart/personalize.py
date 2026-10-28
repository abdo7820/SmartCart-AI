import json

import pandas as pd

from . import appdb, catalog, config, db, recommend
from .appdb import new_id, now_ms

EMPTY_HIST = pd.DataFrame({"ts": pd.Series(dtype="int64"), "item_id": pd.Series(dtype="int64"), "event_type": pd.Series(dtype="object"),
                           "session_id": pd.Series(dtype="object")})
SOURCE_TEXT = {
    "ctx": "related to products you looked at in your latest visit",
    "cf": "shoppers who looked at products like yours also looked at this",
    "pop": "popular in the shop right now",
    "catpop": "popular in a category you browse",
}


def reason_for(sources, origin):
    parts = [SOURCE_TEXT[s] for s in sources if s in SOURCE_TEXT]
    if parts:
        return "Suggested because it is " + " and ".join(parts) + "."
    if origin == "preference_based":
        return "Suggested because it is popular in a department you chose."
    return "Suggested because it is popular in the shop right now."


def history_frame(con, adb, account_id, profile):
    parts = []
    vid = profile.get("historical_visitor_id") if profile else None
    if vid is not None:
        h = db.frame(con, "SELECT ts, item_id, event_type, session_id FROM events WHERE visitor_id = ? ORDER BY ts, event_id", (int(vid),))
        if len(h):
            parts.append(h.assign(origin="historical"))
    own = adb.query("SELECT ts, item_id, event_type, session_key AS session_id FROM interaction_events WHERE account_id = ? ORDER BY ts, id", (account_id,))
    if own:
        parts.append(pd.DataFrame(own).assign(origin="app"))
    if not parts:
        return EMPTY_HIST.assign(origin=pd.Series(dtype="object"))
    return pd.concat(parts, ignore_index=True).sort_values("ts", kind="stable").reset_index(drop=True)


def record_event(adb, account_id, item_id, event_type):
    ts = now_ms()
    last = adb.one("SELECT ts, session_key FROM interaction_events WHERE account_id = ? ORDER BY ts DESC LIMIT 1", (account_id,))
    session = last["session_key"] if last and ts - last["ts"] <= config.SESSION_GAP_MS else new_id()
    adb.execute("INSERT INTO interaction_events (id, account_id, ts, event_type, item_id, session_key) VALUES (?, ?, ?, ?, ?, ?)",
                (new_id(), account_id, ts, event_type, int(item_id), session))
    return {"ts": ts, "session_key": session}


def _label(origin):
    return {
        "history_based": "ranked by the discovery model from this account's history",
        "preference_based": "popular products in the departments you chose (no history yet)",
        "popularity_based": "popular products (no history or preferences yet)",
    }[origin]


def recommended(con, ranker_svc, hist, prefs, k=12):
    """Returns (items, source). source says what actually produced the list."""
    if len(hist):
        try:
            if ranker_svc is not None:
                items, _ = recommend.ranked_items(con, ranker_svc, hist, "discovery", k, "not_out")
            else:
                items, _ = recommend.hybrid(con, hist.to_dict("records"), k * 4, False, True)
                items = [i for i in items if i["in_stock"] != 0][:k]
        except Exception:
            items = []
        if items:
            for i in items:
                i["reason"] = reason_for(i.get("sources", []), "history_based")
            return items, "history_based"
    if prefs:
        items = catalog.popular(con, k, departments=prefs)
        if items:
            for i in items:
                i["reason"] = reason_for([], "preference_based")
            return items, "preference_based"
    items = catalog.popular(con, k)
    for i in items:
        i["reason"] = reason_for([], "popularity_based")
    return items, "popularity_based"


def recently_viewed(con, hist, k=8):
    if not len(hist):
        return []
    v = hist[hist["event_type"] == "view"]
    ids = list(dict.fromkeys(int(i) for i in reversed(v["item_id"].tolist())))[:k]
    info = catalog.get_products(con, ids)
    return [info[i] for i in ids if i in info]


def sections(con, ranker_svc, adb, account, profile, k=12):
    hist = history_frame(con, adb, account["id"], profile)
    prefs = [d for d in __import__("smartcart.accounts", fromlist=["x"]).get_preferences(adb, account["id"])]
    items, source = recommended(con, ranker_svc, hist, prefs, k)
    out = [{"key": "recommended", "title": "Recommended for you", "source": source, "personalized": source != "popularity_based",
            "note": _label(source), "items": items}]
    viewed = recently_viewed(con, hist)
    if viewed:
        out.append({"key": "recently_viewed", "title": "Recently viewed", "source": "activity", "personalized": True,
                    "note": "products you opened", "items": viewed})
        bought = set(hist.loc[hist["event_type"] == "transaction", "item_id"].astype("int64")) if len(hist) else set()
        sim = catalog.similar(con, viewed[0]["item_id"], 8, "not_out", exclude=bought)
        if sim:
            out.append({"key": "similar", "title": f"Because you viewed {viewed[0]['name']}", "source": "item_similarity", "personalized": True,
                        "note": "products that shoppers often look at in the same visit", "items": sim})
    out.append({"key": "popular", "title": "Popular products", "source": "popularity", "personalized": False,
                "note": "most active products in the last 30 days of the shop's data", "items": catalog.popular(con, 8)})
    if ranker_svc is not None:
        tr = catalog.trending(con, 8)
        if tr:
            out.append({"key": "trending", "title": "Trending", "source": "trend", "personalized": False,
                        "note": "products whose last-7-day activity is rising against their 30-day activity, in the shop's data", "items": tr})
    return out, source, len(hist)


def log_request(adb, account_id, source, n_items):
    adb.execute("INSERT INTO recommendation_requests (id, account_id, ts, source, n_items) VALUES (?, ?, ?, ?, ?)", (new_id(), account_id, now_ms(), source, n_items))
