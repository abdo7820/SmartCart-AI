import json
import sqlite3

import pytest

from conftest import PASSWORD, Session


def test_register_login_me_flow(client, anon):
    r = anon.register("alice@example.com", PASSWORD, name="Alice Doe", country="Egypt")
    assert r.status_code == 201
    body = r.json()
    assert body["account"]["role"] == "user" and body["redirect"] == "/dashboard" and body["csrf_token"]
    assert "password" not in json.dumps(body).lower()
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    me = anon.get("/auth/me").json()
    assert me["account"]["email"] == "alice@example.com" and me["profile"]["origin"] == "new"
    second = Session()
    ok = second.login("ALICE@example.com", PASSWORD)
    assert ok.status_code == 200 and ok.json()["account"]["id"] == body["account"]["id"]


def test_password_is_hashed_never_plain(client, anon):
    anon.register("hash.check@example.com", PASSWORD)
    from smartcart.state import state
    rows = state["adb"].query("SELECT * FROM accounts WHERE email = 'hash.check@example.com'")
    assert rows[0]["password_hash"].startswith("$argon2")
    assert PASSWORD not in json.dumps(rows)
    for table in ("customer_profiles", "auth_sessions", "account_preferences"):
        assert PASSWORD not in json.dumps(state["adb"].query(f"SELECT * FROM {table}"))


def test_duplicate_email_rejected_case_insensitive(client, anon):
    assert anon.register("dup@example.com", PASSWORD).status_code == 201
    other = Session()
    assert other.register("DUP@Example.com", PASSWORD).status_code == 409
    assert other.register("  dup@example.com ", PASSWORD).status_code == 409
    from smartcart.state import state
    assert state["adb"].scalar("SELECT COUNT(*) FROM accounts WHERE email = 'dup@example.com'") == 1


@pytest.mark.parametrize("password,fragment", [
    ("short1", "at least 10"), ("alllettersnodigits", "letters and digits"), ("1234567890123", "letters and digits"), ("Password123", "commonly used"),
    ("zed.rivers-9999", "before the @"),
])
def test_weak_passwords_rejected(client, anon, password, fragment):
    r = anon.register("zed.rivers@example.com", password)
    assert r.status_code == 422
    assert fragment in json.dumps(r.json())


def test_invalid_input_rejected(client, anon):
    assert anon.register("not-an-email", PASSWORD).status_code == 422
    assert anon.register("a@example.com", PASSWORD, name="x").status_code == 422
    assert anon.c.post("/auth/register", json={"email": "a@example.com"}).status_code == 422


def test_client_cannot_choose_role(client, anon):
    r = anon.register("sneaky@example.com", PASSWORD, role="admin")
    assert r.status_code == 422
    from smartcart.state import state
    assert state["adb"].scalar("SELECT COUNT(*) FROM accounts WHERE email = 'sneaky@example.com'") == 0
    assert anon.c.post("/auth/login", json={"email": "x@example.com", "password": PASSWORD, "role": "admin"}).status_code == 422


def test_login_errors_are_generic(client, make_user):
    u = make_user()
    s = Session()
    wrong = s.login(u.email, "Wrong-pass-123")
    unknown = s.login("nobody@example.com", "Wrong-pass-123")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_logout_revokes_session(client, make_user):
    u = make_user()
    token = u.c.cookies.get("sc_session")
    assert u.get("/auth/me").status_code == 200
    assert u.post("/auth/logout").status_code == 200
    assert u.get("/auth/me").status_code == 401
    replay = Session()
    replay.c.cookies.set("sc_session", token)
    assert replay.get("/auth/me").status_code == 401


def test_logout_requires_csrf(client, make_user):
    u = make_user()
    r = u.c.post("/auth/logout")
    assert r.status_code == 403
    assert u.get("/auth/me").status_code == 200


def test_expired_session_rejected(client, make_user):
    u = make_user()
    from smartcart.state import state
    state["adb"].execute("UPDATE auth_sessions SET expires_at = 1 WHERE account_id = ?", (u.account["id"],))
    assert u.get("/auth/me").status_code == 401
    assert u.get("/me").status_code == 401


def test_csrf_and_origin_enforced(client, make_user):
    u = make_user()
    assert u.c.put("/me/preferences", json={"departments": []}).status_code == 403
    assert u.c.put("/me/preferences", json={"departments": []}, headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert u.put("/me/preferences", json={"departments": []}).status_code == 200
    evil = u.c.put("/me/preferences", json={"departments": []}, headers={"X-CSRF-Token": u.csrf, "Origin": "https://evil.example"})
    assert evil.status_code == 403
    assert u.c.post("/auth/login", json={"email": "a@example.com", "password": PASSWORD}, headers={"Origin": "https://evil.example"}).status_code == 403


def test_disabled_account_cannot_login(client, make_user, admin):
    u = make_user()
    assert admin.post(f"/admin/users/{u.account['id']}/disable").status_code == 200
    assert Session().login(u.email, PASSWORD).status_code == 401
    assert u.get("/auth/me").status_code == 401
    assert admin.post(f"/admin/users/{u.account['id']}/enable").status_code == 200
    assert Session().login(u.email, PASSWORD).status_code == 200


def test_login_rate_limit(client, make_user, monkeypatch):
    from smartcart import config, security
    u = make_user()
    monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(config, "LOGIN_MAX_ATTEMPTS", 3)
    security.limiter.reset()
    s = Session()
    codes = [s.login(u.email, "Wrong-pass-123").status_code for _ in range(5)]
    security.limiter.reset()
    assert codes[:3] == [401, 401, 401] and 429 in codes[3:]


def test_register_rate_limit(client, monkeypatch):
    from smartcart import config, security
    monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(config, "REGISTER_MAX_PER_HOUR", 2)
    security.limiter.reset()
    codes = [Session().register(f"rl{i}@example.com", PASSWORD).status_code for i in range(4)]
    security.limiter.reset()
    assert codes[:2] == [201, 201] and codes[2:] == [429, 429]


def test_secure_cookie_flag_in_production(client, monkeypatch):
    from smartcart import config
    monkeypatch.setattr(config, "COOKIE_SECURE", True)
    r = Session().c.post("/auth/register", json={"email": "secure@example.com", "password": PASSWORD, "full_name": "Sec Ure"})
    assert r.status_code == 201 and "secure" in r.headers["set-cookie"].lower()
