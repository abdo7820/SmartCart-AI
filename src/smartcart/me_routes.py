from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from . import accounts, catalog, personalize
from .deps import profile_of, rate_limit, session_user
from .state import state

router = APIRouter(prefix="/me", tags=["me"])


class PreferencesIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    departments: list[str] = Field(max_length=10)


class ProfileIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str | None = Field(default=None, min_length=2, max_length=80)
    country: str | None = Field(default=None, max_length=60)


class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_type: str = Field(pattern="^(view|addtocart)$")
    item_id: int = Field(ge=0)


@router.get("")
def me(acc: dict = Depends(session_user)):
    adb = state["adb"]
    profile = profile_of(acc)
    own = adb.scalar("SELECT COUNT(*) FROM interaction_events WHERE account_id = ?", (acc["id"],))
    return {
        "account": accounts.public_account(acc),
        "profile": {"origin": profile["origin"], "country": profile["country"], "linked_to_historical_customer": profile["historical_visitor_id"] is not None},
        "preferences": accounts.get_preferences(adb, acc["id"]),
        "activity": {"recorded_events": own},
    }


@router.put("/profile")
def update_profile(body: ProfileIn, acc: dict = Depends(session_user)):
    adb = state["adb"]
    with adb.transaction():
        if body.full_name is not None:
            adb.execute("UPDATE accounts SET full_name = ? WHERE id = ?", (" ".join(body.full_name.split()), acc["id"]))
        if "country" in body.model_fields_set:
            adb.execute("UPDATE customer_profiles SET country = ? WHERE account_id = ?", ((body.country or "").strip() or None, acc["id"]))
    return me(accounts.get_account(adb, acc["id"]) | {"csrf_token": acc["csrf_token"]})


@router.get("/preferences")
def get_preferences(acc: dict = Depends(session_user)):
    return {"departments": accounts.get_preferences(state["adb"], acc["id"]), "available": catalog.departments(state["con"])}


@router.put("/preferences")
def put_preferences(body: PreferencesIn, acc: dict = Depends(session_user)):
    known = set(catalog.departments(state["con"]))
    bad = [d for d in body.departments if d not in known]
    if bad:
        raise HTTPException(422, detail=[{"loc": ["body", "departments"], "msg": f"Unknown department: {bad[0]}", "type": "value_error"}])
    accounts.set_preferences(state["adb"], acc["id"], body.departments)
    return {"departments": accounts.get_preferences(state["adb"], acc["id"])}


@router.post("/events", status_code=201)
def post_event(body: EventIn, acc: dict = Depends(session_user)):
    rate_limit(("events", acc["id"]), 120, 60)
    if catalog.get_product(state["con"], body.item_id) is None:
        raise HTTPException(404, "product not found")
    saved = personalize.record_event(state["adb"], acc["id"], body.item_id, body.event_type)
    return {"recorded": True, **saved}


@router.get("/recommendations")
def recommendations(k: int = Query(12, ge=1, le=30), acc: dict = Depends(session_user)):
    adb = state["adb"]
    profile = profile_of(acc)
    secs, source, n_hist = personalize.sections(state["con"], state["ranker"], adb, acc, profile, k)
    personalize.log_request(adb, acc["id"], source, len(secs[0]["items"]))
    return {"source": source, "personalized": source != "popularity_based", "history_events": n_hist,
            "needs_preferences": source == "popularity_based", "sections": secs}


@router.get("/activity")
def activity(limit: int = Query(6, ge=1, le=20), acc: dict = Depends(session_user)):
    rows = state["adb"].query("SELECT ts, event_type, item_id FROM interaction_events WHERE account_id = ? ORDER BY ts DESC LIMIT ?", (acc["id"], limit))
    info = catalog.get_products(state["con"], sorted({int(r["item_id"]) for r in rows}))
    return [{"ts": r["ts"], "event_type": r["event_type"], "product": info.get(int(r["item_id"]))} for r in rows if int(r["item_id"]) in info]
