from conftest import Session


def product_ids(client):
    return {p["item_id"] for p in client.get("/products", params={"limit": 100}).json()["items"]}


def all_items(res):
    return [i for s in res["sections"] for i in s["items"]]


def test_new_user_gets_honest_popularity_fallback(client, make_user):
    u = make_user()
    r = u.get("/me/recommendations").json()
    rec = r["sections"][0]
    assert r["source"] == "popularity_based" and r["personalized"] is False and r["needs_preferences"] is True and r["history_events"] == 0
    assert rec["key"] == "recommended" and rec["personalized"] is False and rec["items"]
    keys = [s["key"] for s in r["sections"]]
    assert "popular" in keys and "recently_viewed" not in keys
    for i in all_items(r):
        assert i["in_stock"] != 0
    assert all(i["item_id"] in product_ids(client) for i in rec["items"])


def test_preferences_drive_cold_start(client, make_user):
    u = make_user()
    assert u.put("/me/preferences", json={"departments": ["Fashion"]}).json()["departments"] == ["Fashion"]
    r = u.get("/me/recommendations").json()
    assert r["source"] == "preference_based" and r["personalized"] is True and r["history_events"] == 0
    assert r["sections"][0]["items"] and all(i["department"] == "Fashion" for i in r["sections"][0]["items"])
    assert u.put("/me/preferences", json={"departments": ["Nope"]}).status_code == 422
    assert u.put("/me/preferences", json={"departments": [], "x": 1}).status_code == 422
    assert u.get("/me/preferences").json()["available"]


def test_recorded_events_switch_to_history_based(client, make_user):
    u = make_user()
    assert u.post("/me/events", json={"event_type": "view", "item_id": 5}).status_code == 201
    assert u.post("/me/events", json={"event_type": "view", "item_id": 6}).status_code == 201
    assert u.post("/me/events", json={"event_type": "addtocart", "item_id": 7}).status_code == 201
    r = u.get("/me/recommendations").json()
    assert r["source"] == "history_based" and r["history_events"] == 3
    rec = r["sections"][0]["items"]
    assert rec and not ({5, 6, 7} & {i["item_id"] for i in rec})
    assert all(i["reason"] and i["in_stock"] != 0 for i in rec)
    viewed = next(s for s in r["sections"] if s["key"] == "recently_viewed")
    assert [i["item_id"] for i in viewed["items"]] == [6, 5]


def test_event_validation_and_sessions(client, make_user):
    u = make_user()
    assert u.post("/me/events", json={"event_type": "transaction", "item_id": 5}).status_code == 422
    assert u.post("/me/events", json={"event_type": "view", "item_id": 999999}).status_code == 404
    assert u.post("/me/events", json={"event_type": "view", "item_id": 5, "account_id": "x"}).status_code == 422
    a = u.post("/me/events", json={"event_type": "view", "item_id": 5}).json()
    b = u.post("/me/events", json={"event_type": "view", "item_id": 6}).json()
    assert a["session_key"] == b["session_key"]
    from smartcart.state import state
    rows = state["adb"].query("SELECT account_id FROM interaction_events WHERE session_key = ?", (a["session_key"],))
    assert {r["account_id"] for r in rows} == {u.account["id"]}


def test_no_leakage_between_accounts(client, make_user):
    a, b = make_user(), make_user()
    a.post("/me/events", json={"event_type": "view", "item_id": 9})
    rb = b.get("/me/recommendations").json()
    assert rb["source"] == "popularity_based" and rb["history_events"] == 0
    assert "recently_viewed" not in [s["key"] for s in rb["sections"]]
    ra = a.get("/me/recommendations").json()
    assert ra["source"] == "history_based"


def test_query_parameters_cannot_change_identity(client, make_user):
    u = make_user()
    base = u.get("/me/recommendations").json()
    spoof = u.get("/me/recommendations", params={"visitor_id": 4, "customer_id": 4}).json()
    assert spoof["source"] == base["source"] == "popularity_based" and spoof["history_events"] == 0


def test_linked_historical_customer_uses_real_history(client, make_user, admin):
    u = make_user()
    assert u.get("/me").json()["profile"]["linked_to_historical_customer"] is False
    r = admin.post(f"/admin/users/{u.account['id']}/link-visitor", json={"visitor_id": 4})
    assert r.status_code == 200
    me = u.get("/me").json()
    assert me["profile"]["origin"] == "linked_historical"
    rec = u.get("/me/recommendations").json()
    assert rec["source"] == "history_based" and rec["history_events"] > 0
    from smartcart.state import state
    from smartcart import db
    touched = {r["item_id"] for r in db.query(state["con"], "SELECT item_id FROM events WHERE visitor_id = 4")}
    assert not (touched & {i["item_id"] for i in rec["sections"][0]["items"]})
    other = make_user()
    assert admin.post(f"/admin/users/{other.account['id']}/link-visitor", json={"visitor_id": 4}).status_code == 409
    assert admin.post(f"/admin/users/{other.account['id']}/link-visitor", json={"visitor_id": 99999999}).status_code == 404
    assert admin.post(f"/admin/users/{u.account['id']}/unlink-visitor").status_code == 200
    assert u.get("/me/recommendations").json()["source"] == "popularity_based"


def test_recommendations_use_existing_pipeline(client, make_user, monkeypatch):
    from smartcart import recommend
    from smartcart.state import state
    calls = []
    real = recommend.ranked_items

    def spy(*a, **kw):
        calls.append(a[3])
        return real(*a, **kw)

    monkeypatch.setattr(recommend, "ranked_items", spy)
    u = make_user()
    u.post("/me/events", json={"event_type": "view", "item_id": 11})
    assert u.get("/me/recommendations").json()["source"] == "history_based"
    assert calls == ["discovery"] and state["ranker"] is not None


def test_ranker_failure_falls_back(client, make_user, monkeypatch):
    from smartcart import recommend
    monkeypatch.setattr(recommend, "ranked_items", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    u = make_user()
    u.post("/me/events", json={"event_type": "view", "item_id": 11})
    r = u.get("/me/recommendations").json()
    assert r["source"] == "popularity_based" and r["sections"][0]["items"]


def test_profile_update(client, make_user):
    u = make_user()
    r = u.put("/me/profile", json={"full_name": "Renamed Person", "country": "Egypt"})
    assert r.status_code == 200 and r.json()["account"]["full_name"] == "Renamed Person" and r.json()["profile"]["country"] == "Egypt"


def test_activity_lists_own_events_only(make_user):
    a, b = make_user(), make_user()
    a.post("/me/events", json={"event_type": "view", "item_id": 3})
    b.post("/me/events", json={"event_type": "addtocart", "item_id": 5})
    ra = a.get("/me/activity").json()
    assert [x["product"]["item_id"] for x in ra] == [3]
    assert ra[0]["event_type"] == "view"
