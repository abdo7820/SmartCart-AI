def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["products"] == 60 and r.json()["churn_model"] == "logreg"


def test_products_filters(client):
    r = client.get("/products", params={"department": "Fashion", "sort": "price_asc", "limit": 5}).json()
    prices = [p["price"] for p in r["items"]]
    assert prices == sorted(prices) and all(p["department"] == "Fashion" for p in r["items"])
    assert client.get("/products", params={"q": "Item 7"}).json()["total"] >= 1
    assert client.get("/products/999999").status_code == 404
    assert client.get("/products", params={"sort": "bad"}).status_code == 422


def test_similar_and_categories(client):
    assert client.get("/products/1/similar").json()["items"]
    assert len(client.get("/categories").json()) == 3


def test_recommendations(client, admin):
    r = admin.get("/customers/1/recommendations", params={"k": 5}).json()
    assert r["mode"] == "personalised" and 0 < len(r["items"]) <= 5
    ids = [i["item_id"] for i in r["items"]]
    assert len(ids) == len(set(ids))
    cold = admin.get("/customers/424242/recommendations").json()
    assert cold["mode"] == "cold_start" and cold["items"]


def test_recommendations_exclude_bought(client, admin):
    bought = admin.get("/customers/4/recommendations", params={"k": 50}).json()
    ids = {i["item_id"] for i in bought["items"]}
    import smartcart.app as a
    got = {r[0] for r in a.state["con"].execute("SELECT item_id FROM events WHERE visitor_id = 4 AND event_type = 'transaction'")}
    assert not (ids & got)


def test_churn_buyer(client, admin):
    r = admin.get("/customers/4/churn").json()
    assert r["scored"] and 0 <= r["churn_probability"] <= 1 and r["tier"] in ("High", "Medium", "Low")
    assert len(r["reasons"]) == 3 and r["action"]


def test_churn_non_buyer(client, admin):
    r = admin.get("/customers/1/churn").json()
    assert r["scored"] is False


def test_churn_unknown(client, admin):
    assert admin.get("/customers/424242/churn").status_code == 404


def test_at_risk(client, admin):
    r = admin.get("/churn/at-risk", params={"tier": "High"}).json()
    probs = [i["churn_probability"] for i in r["items"]]
    assert probs == sorted(probs, reverse=True)


def test_models(client, admin):
    r = admin.get("/models").json()
    assert len(r["models"]) == 18 and r["churn_threshold"] == 0.835


def test_ranker_tasks(client, admin):
    assert client.get("/health").json()["ranker"] is True
    for task in ("discovery", "purchase"):
        r = admin.get("/customers/4/recommendations", params={"task": task, "k": 5}).json()
        assert r["task"] == task and len(r["items"]) <= 5
        ids = [i["item_id"] for i in r["items"]]
        assert len(ids) == len(set(ids))
        scores = [i["score"] for i in r["items"]]
        assert scores == sorted(scores, reverse=True)


def test_discovery_excludes_touched(client, admin):
    import smartcart.app as a
    touched = {r[0] for r in a.state["con"].execute("SELECT item_id FROM events WHERE visitor_id = 1")}
    r = admin.get("/customers/1/recommendations", params={"task": "discovery", "k": 50}).json()
    assert r["items"] and not ({i["item_id"] for i in r["items"]} & touched)


def test_ranker_cold_start(client, admin):
    r = admin.get("/customers/424242/recommendations", params={"task": "discovery"}).json()
    assert r["mode"] == "cold_start" and r["items"]


def test_hybrid_still_available(client, admin):
    r = admin.get("/customers/1/recommendations", params={"task": "hybrid"}).json()
    assert r["task"] == "hybrid" and r["items"]
