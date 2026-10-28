import json
import re
import sqlite3

from . import appdb, config, security
from .appdb import new_id, now_ms


class DuplicateEmail(Exception):
    pass


def _is_unique_violation(e):
    if isinstance(e, sqlite3.IntegrityError):
        return "UNIQUE" in str(e).upper()
    try:
        import psycopg

        return isinstance(e, psycopg.errors.UniqueViolation)
    except ImportError:
        return False


def public_account(a):
    return {"id": a["id"], "email": a["email"], "full_name": a["full_name"], "role": a["role"], "is_active": bool(a["is_active"]), "created_at": a["created_at"]}


def create_account(adb, email, full_name, password, role="user", country=None):
    email = security.normalize_email(email)
    aid, pid, ts = new_id(), new_id(), now_ms()
    pw = security.hash_password(password)
    try:
        with adb.transaction():
            adb.execute("INSERT INTO accounts (id, email, full_name, password_hash, role, is_active, created_at) VALUES (?, ?, ?, ?, ?, 1, ?)",
                        (aid, email, full_name.strip(), pw, role, ts))
            adb.execute("INSERT INTO customer_profiles (id, account_id, origin, historical_visitor_id, country, created_at) VALUES (?, ?, 'new', NULL, ?, ?)",
                        (pid, aid, country, ts))
            adb.execute("INSERT INTO account_preferences (account_id, departments, updated_at) VALUES (?, '[]', ?)", (aid, ts))
    except Exception as e:
        if _is_unique_violation(e):
            raise DuplicateEmail(email)
        raise
    return get_account(adb, aid)


def get_account(adb, account_id):
    return adb.one("SELECT * FROM accounts WHERE id = ?", (account_id,))


def get_account_by_email(adb, email):
    try:
        email = security.normalize_email(email)
    except ValueError:
        return None
    return adb.one("SELECT * FROM accounts WHERE email = ?", (email,))


def get_profile(adb, account_id):
    return adb.one("SELECT * FROM customer_profiles WHERE account_id = ?", (account_id,))


def get_preferences(adb, account_id):
    r = adb.one("SELECT departments FROM account_preferences WHERE account_id = ?", (account_id,))
    return json.loads(r["departments"]) if r else []


def set_preferences(adb, account_id, departments):
    ts = now_ms()
    payload = json.dumps(sorted(set(departments)))
    with adb.transaction():
        updated = adb.execute("UPDATE account_preferences SET departments = ?, updated_at = ? WHERE account_id = ?", (payload, ts, account_id))
        if getattr(updated, "rowcount", 1) == 0:
            adb.execute("INSERT INTO account_preferences (account_id, departments, updated_at) VALUES (?, ?, ?)", (account_id, payload, ts))


def create_session(adb, account_id):
    token = security.new_token()
    csrf = security.new_token()
    ts = now_ms()
    adb.execute("INSERT INTO auth_sessions (token_hash, account_id, csrf_token, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
                (security.hash_token(token), account_id, csrf, ts, ts + config.SESSION_TTL_HOURS * 3_600_000))
    adb.execute("UPDATE accounts SET last_login_at = ? WHERE id = ?", (ts, account_id))
    return token, csrf


def session_account(adb, token):
    if not token:
        return None
    row = adb.one("SELECT s.csrf_token, s.expires_at, s.token_hash, a.* FROM auth_sessions s JOIN accounts a ON a.id = s.account_id WHERE s.token_hash = ?",
                  (security.hash_token(token),))
    if row is None:
        return None
    if row["expires_at"] <= now_ms():
        adb.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (row["token_hash"],))
        return None
    if not row["is_active"]:
        return None
    return row


def delete_session(adb, token):
    adb.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (security.hash_token(token),))


def revoke_account_sessions(adb, account_id):
    adb.execute("DELETE FROM auth_sessions WHERE account_id = ?", (account_id,))


def audit(adb, actor_id, action, target=None, details=None):
    adb.execute("INSERT INTO audit_events (id, ts, actor_account_id, action, target, details) VALUES (?, ?, ?, ?, ?, ?)",
                (new_id(), now_ms(), actor_id, action, target, json.dumps(details or {})))


def provision_admin(adb, email, full_name, password, promote=False):
    existing = get_account_by_email(adb, email)
    if existing is None:
        problems = security.password_problems(password, email, full_name)
        if problems:
            raise ValueError("password must have: " + "; ".join(problems))
        acc = create_account(adb, email, full_name, password, role="admin")
        audit(adb, None, "admin_provisioned", acc["id"], {"how": "created"})
        return acc, "created"
    if existing["role"] == "admin":
        return existing, "already_admin"
    if not promote:
        raise ValueError("the account exists with role 'user'; pass promote=True to promote it")
    adb.execute("UPDATE accounts SET role = 'admin' WHERE id = ?", (existing["id"],))
    revoke_account_sessions(adb, existing["id"])
    audit(adb, None, "admin_provisioned", existing["id"], {"how": "promoted"})
    return get_account(adb, existing["id"]), "promoted"
