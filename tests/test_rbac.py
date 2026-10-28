import pytest

from conftest import PASSWORD, Session

ADMIN_GETS = ["/admin/overview", "/admin/users", "/admin/churn", "/admin/models", "/admin/health", "/admin/audit", "/customers/4", "/customers/4/churn",
              "/customers/4/recommendations", "/churn/at-risk", "/models"]
USER_ROUTES = ["/me", "/me/recommendations", "/me/preferences", "/chat/conversations", "/auth/me"]


@pytest.mark.parametrize("url", ADMIN_GETS + USER_ROUTES)
def test_anonymous_gets_401(client, anon, url):
    assert anon.get(url).status_code == 401


def test_anonymous_cannot_write(client, anon):
    assert anon.post("/chat", json={"message": "hi"}).status_code == 401
    assert anon.post("/me/events", json={"event_type": "view", "item_id": 1}).status_code == 401
    assert anon.put("/me/preferences", json={"departments": []}).status_code == 401
    assert anon.post("/admin/users/x/disable").status_code == 401


@pytest.mark.parametrize("url", ADMIN_GETS)
def test_regular_user_gets_403_on_admin_data(client, make_user, url):
    assert make_user().get(url).status_code == 403


def test_regular_user_cannot_use_admin_actions(client, make_user):
    u, victim = make_user(), make_user()
    assert u.post(f"/admin/users/{victim.account['id']}/disable").status_code == 403
    assert u.post(f"/admin/users/{victim.account['id']}/link-visitor", json={"visitor_id": 4}).status_code == 403
    assert Session().login(victim.email, PASSWORD).status_code == 200


def test_public_catalog_stays_public(client, anon):
    for url in ("/health", "/products", "/products/1", "/products/1/similar", "/categories"):
        assert anon.get(url).status_code == 200


def test_client_supplied_role_or_identity_is_ignored(client, make_user):
    u = make_user()
    assert u.put("/me/profile", json={"role": "admin"}).status_code == 422
    assert u.put("/me/profile", json={"full_name": "New Name", "account_id": "x"}).status_code == 422
    assert u.get("/me").json()["account"]["role"] == "user"
    assert u.get("/admin/overview").status_code == 403
    other = make_user()
    assert u.get("/me", params={"account_id": other.account["id"]}).json()["account"]["id"] == u.account["id"]
    assert u.get("/me/recommendations", params={"visitor_id": 4, "account_id": other.account["id"]}).json()["history_events"] == 0


def test_conversations_are_private(client, make_user):
    a, b = make_user(), make_user()
    cid = a.post("/chat", json={"message": "Show me popular products"}).json()["conversation_id"]
    assert b.get(f"/chat/conversations/{cid}").status_code == 404
    assert b.delete(f"/chat/conversations/{cid}").status_code == 404
    assert b.post("/chat", json={"message": "hello", "conversation_id": cid}).status_code == 404
    assert cid not in [c["id"] for c in b.get("/chat/conversations").json()]
    assert a.get(f"/chat/conversations/{cid}").status_code == 200


def test_admin_provisioning_is_controlled(client):
    from smartcart import accounts
    from smartcart.state import state
    adb = state["adb"]
    acc, how = accounts.provision_admin(adb, "boss@example.com", "The Boss", PASSWORD)
    assert how == "created" and acc["role"] == "admin"
    assert accounts.provision_admin(adb, "boss@example.com", "The Boss", PASSWORD)[1] == "already_admin"
    s = Session()
    s.register("future.admin@example.com", PASSWORD)
    with pytest.raises(ValueError):
        accounts.provision_admin(adb, "future.admin@example.com", "X Y", PASSWORD)
    assert s.get("/admin/overview").status_code == 403
    with pytest.raises(ValueError):
        accounts.provision_admin(adb, "weak@example.com", "Weak Admin", "short")
    accounts.provision_admin(adb, "future.admin@example.com", "X Y", PASSWORD, promote=True)
    assert s.get("/auth/me").status_code == 401
    fresh = Session()
    r = fresh.login("future.admin@example.com", PASSWORD)
    assert r.json()["redirect"] == "/admin" and fresh.get("/admin/overview").status_code == 200
    actions = [a["action"] for a in state["adb"].query("SELECT action FROM audit_events")]
    assert actions.count("admin_provisioned") >= 2


def test_admin_cannot_disable_self(client, admin):
    me = admin.get("/auth/me").json()["account"]["id"]
    assert admin.post(f"/admin/users/{me}/disable").status_code == 400
