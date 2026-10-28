
from conftest import PASSWORD, Session


def test_overview_reports_real_counts(client, admin, make_user):
    make_user()
    r = admin.get("/admin/overview").json()
    from smartcart.state import state

    assert r["accounts"]["total"] == state["adb"].scalar(
        "SELECT COUNT(*) FROM accounts"
    )
    assert (
        r["accounts"]["admins"] >= 1
        and r["accounts"]["active"] <= r["accounts"]["total"]
    )
    assert r["historical_dataset"]["products"] == 60
    assert r["historical_dataset"]["customers"] == 80
    assert r["historical_dataset"]["events"] > 0
    assert set(r["customer_profiles"]) == {
        "new_application_profiles",
        "linked_to_historical_customer",
    }
    assert r["application_activity"]["recorded_events"] == state["adb"].scalar(
        "SELECT COUNT(*) FROM interaction_events"
    )


def test_recommendation_requests_are_counted(client, admin, make_user):
    before = {
        x["source"]: x["requests"]
        for x in admin.get("/admin/overview").json()[
            "application_activity"
        ]["recommendation_requests"]
    }

    make_user().get("/me/recommendations")

    after = {
        x["source"]: x["requests"]
        for x in admin.get("/admin/overview").json()[
            "application_activity"
        ]["recommendation_requests"]
    }

    assert (
        after.get("popularity_based", 0)
        == before.get("popularity_based", 0) + 1
    )


def test_user_listing_never_exposes_secrets(client, admin, make_user):
    u = make_user()
    r = admin.get("/admin/users", params={"q": u.email[:12]}).json()

    assert r["total"] >= 1

    text = str(r)
    assert "password" not in text
    assert "argon2" not in text
    assert "csrf" not in text
    assert any(i["email"] == u.email for i in r["items"])


def test_churn_analytics(client, admin):
    r = admin.get("/admin/churn", params={"candidates": 50}).json()

    assert r["scored"] == sum(t["customers"] for t in r["tiers"])
    assert r["thresholds"]["high_from"] == 0.835

    probs = [t["churn_probability"] for t in r["top"]]
    assert probs == sorted(probs, reverse=True)


def test_models_and_health(client, admin):
    m = admin.get("/admin/models").json()

    assert len(m["models"]) == 18
    assert m["serving"]["ranker_loaded"] is True
    assert m["environment"]["scikit_learn"]

    h = admin.get("/admin/health").json()
    assert h["catalog_database"]["ok"]
    assert h["application_database"]["ok"]
    assert h["llm_configured"] is False
    assert "001_accounts.sql" in h["application_database"]["migrations"]


def test_audit_log_records_sensitive_actions(client, admin, make_user):
    u = make_user()

    admin.post(f"/admin/users/{u.account['id']}/disable")
    admin.post(
        f"/admin/users/{u.account['id']}/link-visitor",
        json={"visitor_id": 8},
    )

    rows = admin.get("/admin/audit").json()
    actions = {(r["action"], r["target"]) for r in rows}

    assert ("account_disabled", u.account["id"]) in actions
    assert ("visitor_linked", u.account["id"]) in actions
    assert all(
        r["actor_email"] == "root@example.com"
        for r in rows
        if r["action"] in ("account_disabled", "visitor_linked")
    )


def test_admin_login_is_audited(client, admin_credentials):
    s = Session()
    s.login(*admin_credentials)

    from smartcart.state import state

    assert state["adb"].scalar(
        "SELECT COUNT(*) FROM audit_events WHERE action = 'admin_login'"
    ) >= 1


def test_migrations_are_idempotent_and_non_destructive(tmp_path):
    from smartcart import appdb

    adb = appdb.AppDB(path=tmp_path / "fresh.db")

    migrations = appdb.migrate(adb)
    assert migrations == [
        "001_accounts.sql",
        "002_dashboard_indexes.sql",
    ]

    adb.execute(
        "INSERT INTO accounts "
        "(id, email, full_name, password_hash, role, is_active, created_at) "
        "VALUES ('1','a@b.co','A B','x','user',1,1)"
    )

    assert appdb.migrate(adb) == []
    assert adb.scalar("SELECT COUNT(*) FROM accounts") == 1


def test_tests_use_isolated_databases(client):
    from smartcart import config

    assert (
        "tmp" in str(config.APP_DATABASE_PATH).lower()
        or "pytest" in str(config.APP_DATABASE_PATH).lower()
    )
    assert str(config.DATABASE_PATH).endswith("test.db")


def test_dataset_activity_shape(admin):
    r = admin.get("/admin/activity?days=14")

    assert r.status_code == 200

    j = r.json()
    assert len(j["daily"]) == 14
    assert sum(d["views"] for d in j["daily"]) > 0
    assert j["top_purchased"]
    assert j["views_by_department"]


def test_dataset_activity_needs_admin(make_user):
    u = make_user()
    assert u.get("/admin/activity").status_code == 403
