import json
import time

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from . import accounts, config, db
from .appdb import now_ms
from .deps import admin_user
from .state import state

router = APIRouter(prefix="/admin", tags=["admin"])
DAY_MS = 86_400_000


class LinkIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    visitor_id: int = Field(ge=0)


def _targets(adb, account_id):
    t = accounts.get_account(adb, account_id)
    if t is None:
        raise HTTPException(404, "account not found")
    return t


def _utc_iso(ms):
    return pd.Timestamp(int(ms), unit="ms", tz="UTC").isoformat()


def _system_status():
    out = {}
    t = time.perf_counter()
    try:
        state["con"].execute("SELECT 1 AS x").fetchone()
        out["catalog_database"] = {"ok": True, "ms": round((time.perf_counter() - t) * 1000, 1), "backend": "postgresql" if getattr(state["con"], "is_pg", False) else "sqlite"}
    except Exception as e:
        out["catalog_database"] = {"ok": False, "error": type(e).__name__}
    t = time.perf_counter()
    try:
        state["adb"].scalar("SELECT 1")
        out["application_database"] = {"ok": True, "ms": round((time.perf_counter() - t) * 1000, 1), "backend": "postgresql" if state["adb"].is_pg else "sqlite",
                                        "migrations": [r["name"] for r in state["adb"].query("SELECT name FROM app_migrations ORDER BY name")]}
    except Exception as e:
        out["application_database"] = {"ok": False, "error": type(e).__name__}
    out["churn_model_loaded"] = bool(state.get("churn"))
    out["ranker_loaded"] = bool(state.get("ranker"))
    out["llm_configured"] = state.get("chat") is not None and state["chat"].provider is not None
    out["llm_provider"] = state["chat"].provider.name if out["llm_configured"] else None
    return out


def _churn_summary(candidates=2000):
    model = state.get("churn")
    if model is None:
        return {"available": False, "reason": "churn model is unavailable", "candidate_customers": 0, "scored_customers": 0, "tiers": []}
    con = state["con"]
    ids = [r["visitor_id"] for r in db.query(con, "SELECT visitor_id FROM customers WHERE n_orders > 0 ORDER BY last_seen_ts DESC LIMIT ?", (candidates,))]
    if not ids:
        return {"available": True, "candidate_customers": 0, "scored_customers": 0, "tiers": [], "reason": "no historical customers with a purchase"}
    marks = ",".join("?" * len(ids))
    ev = db.frame(con, f"SELECT visitor_id, ts, event_type, item_id, order_id FROM events WHERE visitor_id IN ({marks})", ids)
    res = model.score(ev, state["cutoff"])
    df = pd.DataFrame(res)
    tiers = []
    scored = len(df)
    for tier in ("High", "Medium", "Low"):
        count = int((df["tier"] == tier).sum()) if scored else 0
        tiers.append({"tier": tier, "customers": count, "percentage": round(count / scored * 100, 1) if scored else 0,
                      "mean_probability": float(df.loc[df["tier"] == tier, "churn_probability"].mean()) if count else None})
    return {"available": True, "candidate_customers": len(ids), "scored_customers": scored, "tiers": tiers,
            "scored_at": _utc_iso(now_ms()), "cutoff": _utc_iso(state["cutoff"]), "model_version": model.name,
            "thresholds": {"high_from": model.threshold, "medium_from": model.low_cut},
            "definition": model.definition}


def _recent_audit(limit=8):
    rows = state["adb"].query("""SELECT e.ts, e.action, e.target, a.email AS actor_email
                                 FROM audit_events e LEFT JOIN accounts a ON a.id = e.actor_account_id
                                 ORDER BY e.ts DESC LIMIT ?""", (limit,))
    return [{**r, "ts_iso": _utc_iso(r["ts"])} for r in rows]


@router.get("/action-center")
def action_center(days: int = Query(30, ge=1, le=90), acc: dict = Depends(admin_user)):
    """Admin-only operational summary. All values are sourced from live stores or model artifacts."""
    adb, con = state["adb"], state["con"]
    now = now_ms()
    start = now - days * DAY_MS
    system = _system_status()
    app = {
        "recorded_events": adb.scalar("SELECT COUNT(*) FROM interaction_events"),
        "recorded_events_period": adb.scalar("SELECT COUNT(*) FROM interaction_events WHERE ts >= ?", (start,)),
        "chat_conversations": adb.scalar("SELECT COUNT(*) FROM chat_conversations"),
        "chat_conversations_period": adb.scalar("SELECT COUNT(*) FROM chat_conversations WHERE created_at >= ?", (start,)),
        "chat_messages": adb.scalar("SELECT COUNT(*) FROM chat_messages"),
        "chat_messages_period": adb.scalar("SELECT COUNT(*) FROM chat_messages WHERE created_at >= ?", (start,)),
        "recommendation_requests": adb.scalar("SELECT COUNT(*) FROM recommendation_requests"),
        "recommendation_requests_period": adb.scalar("SELECT COUNT(*) FROM recommendation_requests WHERE ts >= ?", (start,)),
    }
    last_ts = int(con.execute("SELECT MAX(ts) AS m FROM events").fetchone()["m"])
    last_day = last_ts // DAY_MS
    first_day = last_day - days + 1
    rows = db.query(
        con,
        """
        SELECT d, event_type, COUNT(*) AS n
        FROM (
            SELECT ts / ? AS d, event_type
            FROM events
            WHERE ts >= ?
        ) AS daily_events
        GROUP BY d, event_type
        """,
        (DAY_MS, first_day * DAY_MS),
    )
    by_day = {}
    for row in rows:
        by_day.setdefault(int(row["d"]), {})[row["event_type"]] = int(row["n"])
    daily = []
    for day in range(first_day, last_day + 1):
        values = by_day.get(day, {})
        daily.append({"date": str(pd.Timestamp(day * DAY_MS, unit="ms").date()), "views": values.get("view", 0),
                      "addtocart": values.get("addtocart", 0), "transactions": values.get("transaction", 0)})
    dept = db.query(con, "SELECT department, SUM(n_views) AS views FROM products GROUP BY department ORDER BY views DESC")
    top = db.query(con, "SELECT item_id, name, department, n_views, n_carts, n_purchases FROM products ORDER BY n_purchases DESC, n_views DESC LIMIT 5")
    env = json.loads((config.MODELS_DIR / "environment.json").read_text())
    rec_cfg = json.loads((config.MODELS_DIR / "recommendation_config.json").read_text())
    metrics = _csv("recommendation_model_metrics.csv")
    alerts = []
    if not system["catalog_database"]["ok"] or not system["application_database"]["ok"]:
        alerts.append({"severity": "critical", "title": "Database health problem", "detail": "One or more application databases failed the health check.", "href": "/admin/health"})
    if not system["ranker_loaded"]:
        alerts.append({"severity": "warning", "title": "Recommendation ranker unavailable", "detail": "Serving is using the fallback path until ranker state is rebuilt.", "href": "/admin/models"})
    if not system["churn_model_loaded"]:
        alerts.append({"severity": "warning", "title": "Churn model unavailable", "detail": "Churn scoring cannot be trusted until the model loads.", "href": "/admin/churn"})
    if not system["llm_configured"]:
        alerts.append({"severity": "info", "title": "AI provider not configured", "detail": "The deterministic catalog assistant remains available; no external LLM is configured.", "href": "/admin/models"})
    if app["chat_conversations_period"] == 0 and app["recommendation_requests_period"] == 0:
        alerts.append({"severity": "info", "title": "No user activity recorded", "detail": f"No assistant conversations or recommendation requests were recorded in the last {days} days.", "href": "/admin/users"})
    churn = _churn_summary()
    return {
        "last_updated": _utc_iso(now), "window": {"days": days, "start": _utc_iso(start), "end": _utc_iso(now), "timezone": "UTC"},
        "kpis": {"accounts": adb.scalar("SELECT COUNT(*) FROM accounts"), "active_accounts": adb.scalar("SELECT COUNT(*) FROM accounts WHERE is_active = 1"),
                 "new_accounts_period": adb.scalar("SELECT COUNT(*) FROM accounts WHERE created_at >= ?", (start,)), "products": con.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"], **app},
        "application_activity": app,
        "activity": {"daily": daily, "views_by_department": dept, "top_purchased": top, "data_ends_at": _utc_iso(last_ts)},
        "retention": churn,
        "model_ops": {"ranker_loaded": system["ranker_loaded"], "churn_model_loaded": system["churn_model_loaded"],
                      "churn_model_version": env.get("selected_churn_model"), "churn_artifact_created": env.get("created_utc"),
                      "discovery_serving": rec_cfg["discovery"]["final_model"], "purchase_serving": rec_cfg["purchase"]["final_model"],
                      "ai_provider_configured": system["llm_configured"], "ai_provider": system["llm_provider"],
                      "recommendation_metrics": metrics,
                      "evaluation": {"available": bool(metrics), "metric": "NDCG@10", "source": "models/recommendation_model_metrics.csv",
                                     "dataset": None, "evaluated_at": None, "note": "Evaluation dataset and date are not recorded in the exported metrics artifact."}},
        "system": system, "alerts": alerts, "recent_admin_activity": _recent_audit(),
        "observability": {"auth_failures": {"available": False, "reason": "Authentication failures are process-log events, not persisted in the application database."},
                           "rate_limits": {"available": False, "reason": "Rate-limit events are process-local and not persisted."}},
    }


@router.get("/overview")
def overview(acc: dict = Depends(admin_user)):
    adb, con = state["adb"], state["con"]
    week = now_ms() - 7 * DAY_MS
    last_ts = con.execute("SELECT MAX(ts) AS m FROM events").fetchone()["m"]
    ev_total = con.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"]
    ev_week = con.execute("SELECT COUNT(*) AS n FROM events WHERE ts >= ?", (int(last_ts) - 7 * DAY_MS,)).fetchone()["n"]
    reco = adb.query("SELECT source, COUNT(*) AS requests FROM recommendation_requests GROUP BY source")
    return {
        "accounts": {
            "total": adb.scalar("SELECT COUNT(*) FROM accounts"),
            "active": adb.scalar("SELECT COUNT(*) FROM accounts WHERE is_active = 1"),
            "admins": adb.scalar("SELECT COUNT(*) FROM accounts WHERE role = 'admin'"),
            "new_last_7_days": adb.scalar("SELECT COUNT(*) FROM accounts WHERE created_at >= ?", (week,)),
        },
        "customer_profiles": {
            "new_application_profiles": adb.scalar("SELECT COUNT(*) FROM customer_profiles WHERE origin = 'new'"),
            "linked_to_historical_customer": adb.scalar("SELECT COUNT(*) FROM customer_profiles WHERE origin = 'linked_historical'"),
        },
        "historical_dataset": {
            "customers": con.execute("SELECT COUNT(*) AS n FROM customers").fetchone()["n"],
            "products": con.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"],
            "events": ev_total, "events_in_last_7_days_of_data": ev_week,
            "data_ends_at": str(pd.Timestamp(int(last_ts), unit="ms")),
            "enrichment_origin": state["info"].get("enrichment_origin"),
        },
        "application_activity": {
            "recorded_events": adb.scalar("SELECT COUNT(*) FROM interaction_events"),
            "recorded_events_last_7_days": adb.scalar("SELECT COUNT(*) FROM interaction_events WHERE ts >= ?", (week,)),
            "chat_conversations": adb.scalar("SELECT COUNT(*) FROM chat_conversations"),
            "chat_messages": adb.scalar("SELECT COUNT(*) FROM chat_messages"),
            "recommendation_requests": reco,
        },
    }


@router.get("/users")
def users(q: str | None = None, limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0), acc: dict = Depends(admin_user)):
    adb = state["adb"]
    where, params = "", []
    if q:
        where = "WHERE LOWER(a.email) LIKE ? OR LOWER(a.full_name) LIKE ?"
        params = [f"%{q.lower()}%"] * 2
    total = adb.scalar(f"SELECT COUNT(*) FROM accounts a {where}", params)
    rows = adb.query(f"""SELECT a.id, a.email, a.full_name, a.role, a.is_active, a.created_at, a.last_login_at, p.origin, p.historical_visitor_id
                         FROM accounts a JOIN customer_profiles p ON p.account_id = a.id {where} ORDER BY a.created_at DESC LIMIT ? OFFSET ?""", [*params, limit, offset])
    return {"total": total, "items": rows}


@router.post("/users/{account_id}/disable")
def disable(account_id: str, acc: dict = Depends(admin_user)):
    t = _targets(state["adb"], account_id)
    if t["id"] == acc["id"]:
        raise HTTPException(400, "You cannot disable your own account")
    with state["adb"].transaction():
        state["adb"].execute("UPDATE accounts SET is_active = 0 WHERE id = ?", (account_id,))
        accounts.revoke_account_sessions(state["adb"], account_id)
        accounts.audit(state["adb"], acc["id"], "account_disabled", account_id)
    return {"id": account_id, "is_active": False}


@router.post("/users/{account_id}/enable")
def enable(account_id: str, acc: dict = Depends(admin_user)):
    _targets(state["adb"], account_id)
    with state["adb"].transaction():
        state["adb"].execute("UPDATE accounts SET is_active = 1 WHERE id = ?", (account_id,))
        accounts.audit(state["adb"], acc["id"], "account_enabled", account_id)
    return {"id": account_id, "is_active": True}


@router.post("/users/{account_id}/link-visitor")
def link_visitor(account_id: str, body: LinkIn, acc: dict = Depends(admin_user)):
    adb = state["adb"]
    _targets(adb, account_id)
    if db.one(state["con"], "SELECT 1 AS x FROM customers WHERE visitor_id = ?", (body.visitor_id,)) is None:
        raise HTTPException(404, "historical customer not found")
    taken = adb.one("SELECT account_id FROM customer_profiles WHERE historical_visitor_id = ?", (body.visitor_id,))
    if taken and taken["account_id"] != account_id:
        raise HTTPException(409, "that historical customer is already linked to another account")
    with adb.transaction():
        adb.execute("UPDATE customer_profiles SET historical_visitor_id = ?, origin = 'linked_historical' WHERE account_id = ?", (body.visitor_id, account_id))
        accounts.audit(adb, acc["id"], "visitor_linked", account_id, {"visitor_id": body.visitor_id})
    return {"id": account_id, "historical_visitor_id": body.visitor_id}


@router.post("/users/{account_id}/unlink-visitor")
def unlink_visitor(account_id: str, acc: dict = Depends(admin_user)):
    adb = state["adb"]
    _targets(adb, account_id)
    with adb.transaction():
        adb.execute("UPDATE customer_profiles SET historical_visitor_id = NULL, origin = 'new' WHERE account_id = ?", (account_id,))
        accounts.audit(adb, acc["id"], "visitor_unlinked", account_id)
    return {"id": account_id, "historical_visitor_id": None}


@router.get("/activity")
def dataset_activity(days: int = Query(30, ge=7, le=90), acc: dict = Depends(admin_user)):
    con = state["con"]
    last = int(con.execute("SELECT MAX(ts) AS m FROM events").fetchone()["m"])
    last_day = last // DAY_MS
    first_day = last_day - days + 1
    rows = db.query(
        con,
        """
        SELECT d, event_type, COUNT(*) AS n
        FROM (
            SELECT ts / ? AS d, event_type
            FROM events
            WHERE ts >= ?
        ) AS daily_events
        GROUP BY d, event_type
        """,
        (DAY_MS, first_day * DAY_MS),
    )
    by = {}
    for r in rows:
        by.setdefault(int(r["d"]), {})[r["event_type"]] = int(r["n"])
    daily = []
    for d in range(first_day, last_day + 1):
        e = by.get(d, {})
        daily.append({"date": str(pd.Timestamp(d * DAY_MS, unit="ms").date()), "views": e.get("view", 0), "addtocart": e.get("addtocart", 0), "transactions": e.get("transaction", 0)})
    dept = db.query(con, "SELECT department, SUM(n_views) AS views FROM products GROUP BY department ORDER BY views DESC")
    top = db.query(con, "SELECT item_id, name, department, n_views, n_carts, n_purchases FROM products ORDER BY n_purchases DESC, n_views DESC LIMIT 5")
    orders = db.query(con, "SELECT COUNT(*) AS n FROM orders")[0]["n"]
    return {"daily": daily, "views_by_department": dept, "top_purchased": top, "dataset_orders": orders, "data_ends_at": str(pd.Timestamp(last, unit="ms"))}


@router.get("/churn")
def churn(candidates: int = Query(2000, ge=50, le=5000), acc: dict = Depends(admin_user)):
    con = state["con"]
    ids = [r["visitor_id"] for r in db.query(con, "SELECT visitor_id FROM customers WHERE n_orders > 0 ORDER BY last_seen_ts DESC LIMIT ?", (candidates,))]
    if not ids:
        return {"scored": 0, "population": "no historical customers with a purchase", "tiers": [], "thresholds": {"high_from": state["churn"].threshold, "medium_from": state["churn"].low_cut}, "definition": state["churn"].definition, "top": []}
    marks = ",".join("?" * len(ids))
    ev = db.frame(con, f"SELECT visitor_id, ts, event_type, item_id, order_id FROM events WHERE visitor_id IN ({marks})", ids)
    res = state["churn"].score(ev, state["cutoff"])
    df = pd.DataFrame(res)
    tiers = [{"tier": t, "customers": int((df["tier"] == t).sum()), "mean_probability": float(df.loc[df["tier"] == t, "churn_probability"].mean()) if (df["tier"] == t).any() else None}
             for t in ("High", "Medium", "Low")]
    top = df.sort_values("churn_probability", ascending=False).head(10)[["visitor_id", "churn_probability", "tier", "action"]].to_dict("records")
    return {"scored": len(df), "population": f"the {len(ids)} most recently active historical customers who bought before", "tiers": tiers,
            "thresholds": {"high_from": state["churn"].threshold, "medium_from": state["churn"].low_cut}, "definition": state["churn"].definition, "top": top}


def _csv(name):
    p = config.MODELS_DIR / name
    if not p.exists():
        return []
    df = pd.read_csv(p).round(4).astype(object)
    return df.where(df.notna(), None).to_dict("records")


@router.get("/models")
def models(acc: dict = Depends(admin_user)):
    manifest = json.loads((config.MODELS_DIR / "model_manifest.json").read_text())
    rec_cfg = json.loads((config.MODELS_DIR / "recommendation_config.json").read_text())
    env = json.loads((config.MODELS_DIR / "environment.json").read_text())
    return {
        "serving": {"churn_model": state["churn"].name, "ranker_loaded": bool(state["ranker"]),
                    "purchase_final": rec_cfg["purchase"]["final_model"], "discovery_final": rec_cfg["discovery"]["final_model"],
                    "churn_threshold": state["churn"].threshold},
        "environment": {k: env.get(k) for k in ("python", "numpy", "pandas", "scikit_learn", "mlflow", "created_utc")},
        "models": [{k: m.get(k) for k in ("model_key", "task", "model_kind", "validation_ndcg_at_10", "test_ndcg_at_10", "selected_final_model")} for m in manifest],
        "recommendation_metrics": _csv("recommendation_model_metrics.csv"),
        "churn_test_metrics": _csv("churn_test_metrics.csv"),
    }


@router.get("/health")
def health(acc: dict = Depends(admin_user)):
    out = {}
    t = time.perf_counter()
    try:
        state["con"].execute("SELECT 1 AS x").fetchone()
        out["catalog_database"] = {"ok": True, "ms": round((time.perf_counter() - t) * 1000, 1), "backend": "postgresql" if getattr(state["con"], "is_pg", False) else "sqlite"}
    except Exception as e:
        out["catalog_database"] = {"ok": False, "error": type(e).__name__}
    t = time.perf_counter()
    try:
        state["adb"].scalar("SELECT 1")
        out["application_database"] = {"ok": True, "ms": round((time.perf_counter() - t) * 1000, 1), "backend": "postgresql" if state["adb"].is_pg else "sqlite",
                                       "migrations": [r["name"] for r in state["adb"].query("SELECT name FROM app_migrations ORDER BY name")]}
    except Exception as e:
        out["application_database"] = {"ok": False, "error": type(e).__name__}
    out["churn_model_loaded"] = bool(state.get("churn"))
    out["ranker_loaded"] = bool(state["ranker"])
    out["llm_configured"] = state.get("chat") is not None and state["chat"].provider is not None
    out["llm_provider"] = state["chat"].provider.name if out["llm_configured"] else None
    return out


@router.get("/audit")
def audit(limit: int = Query(50, ge=1, le=200), acc: dict = Depends(admin_user)):
    rows = state["adb"].query("""SELECT e.ts, e.action, e.target, e.details, a.email AS actor_email FROM audit_events e
                                 LEFT JOIN accounts a ON a.id = e.actor_account_id ORDER BY e.ts DESC LIMIT ?""", (limit,))
    for r in rows:
        r["details"] = json.loads(r["details"])
    return rows
