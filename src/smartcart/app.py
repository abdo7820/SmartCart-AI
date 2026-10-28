import json
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import admin_routes, appdb, auth_routes, chat_routes, config, db, me_routes, ranker, recommend
from .chat import llm as chat_llm, service as chat_service
from .deps import admin_user
from .churn import ChurnService
from .state import state

@asynccontextmanager
async def lifespan(app):
    state["con"] = db.connect()
    state["churn"] = ChurnService()
    state["ranker"] = ranker.RankerService.from_db(state["con"]) if ranker.available(state["con"]) else None
    state["cutoff"] = db.as_of_ms(state["con"])
    state["info"] = db.db_info(state["con"])
    state["adb"] = appdb.open_app_db()
    appdb.migrate(state["adb"])
    state["chat"] = chat_service.ChatService(state["con"], state["ranker"], state["adb"], chat_llm.provider_from_config())
    yield
    state["con"].close()
    state["adb"].close()


app = FastAPI(title="SmartCart AI", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "DELETE"],
                   allow_headers=["Content-Type", "X-CSRF-Token"])
app.include_router(auth_routes.router)
app.include_router(me_routes.router)
app.include_router(chat_routes.router)
app.include_router(admin_routes.router)
PRODUCT_COLS = "item_id, name, brand, product_type, department, category_id, price, currency, price_tier, is_deal, in_stock, n_views, n_carts, n_purchases"


def _events_for(visitor_ids):
    marks = ",".join("?" * len(visitor_ids))
    return db.frame(state["con"], f"SELECT visitor_id, ts, event_type, item_id, order_id FROM events WHERE visitor_id IN ({marks})", list(visitor_ids))


@app.get("/health")
def health():
    n = state["con"].execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"]
    return {"status": "ok", "products": n, "churn_model": state["churn"].name, "ranker": bool(state["ranker"]), "data_origin": state["info"].get("data_origin"),
            "enrichment_origin": state["info"].get("enrichment_origin")}


@app.get("/products")
def products(q: str | None = None, department: str | None = None, min_price: float | None = None, max_price: float | None = None,
             in_stock: bool | None = None, deal: bool | None = None, sort: str = Query("popular", pattern="^(popular|price_asc|price_desc)$"),
             limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    where, params = [], []
    if q:
        where.append("LOWER(name) LIKE ?")
        params.append(f"%{q.lower()}%")
    if department:
        where.append("department = ?")
        params.append(department)
    if min_price is not None:
        where.append("price >= ?")
        params.append(min_price)
    if max_price is not None:
        where.append("price <= ?")
        params.append(max_price)
    if in_stock is not None:
        where.append("in_stock = ?")
        params.append(int(in_stock))
    if deal is not None:
        where.append("is_deal = ?")
        params.append(int(deal))
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    order = {"popular": "popularity_rank ASC", "price_asc": "price ASC", "price_desc": "price DESC"}[sort]
    total = state["con"].execute(f"SELECT COUNT(*) AS n FROM products {clause}", params).fetchone()["n"]
    rows = db.query(state["con"], f"SELECT {PRODUCT_COLS} FROM products {clause} ORDER BY {order} LIMIT ? OFFSET ?", [*params, limit, offset])
    return {"total": total, "items": rows}


@app.get("/products/{item_id}")
def product(item_id: int):
    r = db.one(state["con"], f"SELECT {PRODUCT_COLS}, price_proxy_790, view_to_cart, cart_to_buy, name_is_synthetic, price_is_synthetic FROM products WHERE item_id = ?", (item_id,))
    if r is None:
        raise HTTPException(404, "product not found")
    return r


@app.get("/products/{item_id}/similar")
def similar(item_id: int, k: int = Query(10, ge=1, le=50)):
    if db.one(state["con"], "SELECT 1 AS x FROM products WHERE item_id = ?", (item_id,)) is None:
        raise HTTPException(404, "product not found")
    rows = db.query(state["con"], """SELECT p.item_id, p.name, p.department, p.price, p.in_stock, n.score
                                     FROM item_neighbors n JOIN products p ON p.item_id = n.neighbor_id
                                     WHERE n.item_id = ? ORDER BY n.score DESC LIMIT ?""", (item_id, k))
    return {"item_id": item_id, "items": rows}


@app.get("/categories")
def categories():
    return db.query(state["con"], "SELECT department, COUNT(*) AS products, ROUND(CAST(AVG(price) AS NUMERIC), 2) AS avg_price FROM products GROUP BY department ORDER BY products DESC")


@app.get("/customers/{visitor_id}")
def customer(visitor_id: int, _admin: dict = Depends(admin_user)):
    c = db.one(state["con"], "SELECT * FROM customers WHERE visitor_id = ?", (visitor_id,))
    if c is None:
        raise HTTPException(404, "customer not found")
    f = db.one(state["con"], "SELECT * FROM customer_features WHERE visitor_id = ?", (visitor_id,))
    return {"customer": c, "features": f}


@app.get("/customers/{visitor_id}/recommendations")
def recommendations(visitor_id: int, _admin: dict = Depends(admin_user), k: int = Query(10, ge=1, le=50), in_stock_only: bool = False, exclude_bought: bool = True,
                    task: str = Query("auto", pattern="^(auto|discovery|purchase|hybrid)$")):
    chosen = task
    if chosen == "auto":
        chosen = "discovery" if state["ranker"] else "hybrid"
    if chosen != "hybrid" and not state["ranker"]:
        raise HTTPException(503, "ranker state is not built; run scripts/build_ranker_state.py")
    if chosen == "hybrid":
        items, mode = recommend.recommend(state["con"], visitor_id, k, in_stock_only, exclude_bought)
        method = "hybrid candidates (context, history, popularity) fused with reciprocal rank fusion"
    else:
        items, mode = recommend.recommend_ranked(state["con"], state["ranker"], visitor_id, chosen, k, in_stock_only, exclude_bought)
        name = state["ranker"].models[chosen][0]
        method = f"{chosen}: four candidate sources re-ranked by {name}" if chosen == "purchase" else f"{chosen}: new items only (not touched by the customer), re-ranked by {name}"
    return {"visitor_id": visitor_id, "task": chosen, "mode": mode, "method": method, "items": items}


@app.get("/customers/{visitor_id}/churn")
def churn(visitor_id: int, _admin: dict = Depends(admin_user)):
    if db.one(state["con"], "SELECT 1 AS x FROM customers WHERE visitor_id = ?", (visitor_id,)) is None:
        raise HTTPException(404, "customer not found")
    res = state["churn"].score(_events_for([visitor_id]), state["cutoff"])
    if not res:
        return {"visitor_id": visitor_id, "scored": False, "reason": "the churn model is trained on customers who have bought; this customer has no purchase"}
    return {**res[0], "scored": True, "definition": state["churn"].definition}


@app.get("/churn/at-risk")
def at_risk(_admin: dict = Depends(admin_user), limit: int = Query(20, ge=1, le=200), tier: str = Query("High", pattern="^(High|Medium|Low)$"), candidates: int = Query(2000, ge=10, le=20000)):
    ids = [r["visitor_id"] for r in db.query(state["con"], "SELECT visitor_id FROM customers WHERE n_orders > 0 ORDER BY last_seen_ts DESC LIMIT ?", (candidates,))]
    if not ids:
        return {"scored_customers": 0, "items": []}
    res = state["churn"].score(_events_for(ids), state["cutoff"])
    res = [r for r in res if r["tier"] == tier]
    res.sort(key=lambda r: -r["churn_probability"])
    return {"scored_customers": len(ids), "tier": tier, "items": res[:limit]}


@app.get("/models")
def models(_admin: dict = Depends(admin_user)):
    manifest = json.loads((config.MODELS_DIR / "model_manifest.json").read_text())
    rows = [{k: m.get(k) for k in ("model_key", "task", "model_kind", "file", "validation_ndcg_at_10", "test_ndcg_at_10", "selected_final_model")} for m in manifest]
    return {"models": rows, "churn_threshold": state["churn"].threshold, "churn_low_cut": state["churn"].low_cut}
