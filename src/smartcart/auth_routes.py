import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from . import accounts, config, security
from .deps import check_origin, client_ip, rate_limit, session_user
from .state import state

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


class RegisterIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=254)
    full_name: str = Field(min_length=2, max_length=80)
    password: str = Field(max_length=256)
    country: str | None = Field(default=None, max_length=60)


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)


def _error(field, msg, status=422):
    return HTTPException(status, detail=[{"loc": ["body", field], "msg": msg, "type": "value_error"}])


def _set_cookie(response, token):
    response.set_cookie(config.SESSION_COOKIE, token, max_age=config.SESSION_TTL_HOURS * 3600, httponly=True, secure=config.COOKIE_SECURE,
                        samesite=config.COOKIE_SAMESITE, path="/")


def _clear_cookie(response):
    response.delete_cookie(config.SESSION_COOKIE, path="/", httponly=True, secure=config.COOKIE_SECURE, samesite=config.COOKIE_SAMESITE)


def _landing(acc):
    return "/admin" if acc["role"] == "admin" else "/dashboard"


@router.post("/register", status_code=201)
def register(body: RegisterIn, request: Request, response: Response):
    check_origin(request)
    rate_limit(("register", client_ip(request)), config.REGISTER_MAX_PER_HOUR, 3600, "Too many registrations from this address")
    try:
        email = security.normalize_email(body.email)
    except ValueError:
        raise _error("email", "Enter a valid email address")
    name = " ".join(body.full_name.split())
    if len(name) < 2:
        raise _error("full_name", "Enter your full name")
    problems = security.password_problems(body.password, email, name)
    if problems:
        raise _error("password", "Password must have: " + "; ".join(problems))
    try:
        acc = accounts.create_account(state["adb"], email, name, body.password, role="user", country=(body.country or "").strip() or None)
    except accounts.DuplicateEmail:
        raise HTTPException(409, "An account with this email already exists")
    token, csrf = accounts.create_session(state["adb"], acc["id"])
    _set_cookie(response, token)
    return {"account": accounts.public_account(acc), "csrf_token": csrf, "redirect": _landing(acc)}


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response):
    check_origin(request)
    ip = client_ip(request)
    account_key = ("login", ip, body.email.strip().lower())
    rate_limit(("login-ip", ip), config.LOGIN_MAX_ATTEMPTS * 3, config.LOGIN_WINDOW_S, "Too many login attempts, try again later")
    rate_limit(account_key, config.LOGIN_MAX_ATTEMPTS, config.LOGIN_WINDOW_S, "Too many login attempts, try again later")
    acc = accounts.get_account_by_email(state["adb"], body.email)
    ok = False
    if acc is not None and acc["is_active"]:
        ok = security.verify_password(body.password, acc["password_hash"])
    else:
        security.burn_verification_time(body.password)
    if not ok:
        logger.warning("login_rejected reason=invalid_credentials")
        raise HTTPException(401, "Invalid email or password")
    if security.needs_rehash(acc["password_hash"]):
        state["adb"].execute("UPDATE accounts SET password_hash = ? WHERE id = ?", (security.hash_password(body.password), acc["id"]))
    token, csrf = accounts.create_session(state["adb"], acc["id"])
    # The credentials are verified, so clear only this account+IP bucket.
    # The aggregate IP bucket remains active as a separate brute-force guard.
    security.limiter.reset_key(account_key)
    logger.info("login_succeeded role=%s", acc["role"])
    _set_cookie(response, token)
    if acc["role"] == "admin":
        accounts.audit(state["adb"], acc["id"], "admin_login", acc["id"])
    return {"account": accounts.public_account(acc), "csrf_token": csrf, "redirect": _landing(acc)}


@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(config.SESSION_COOKIE)
    acc = accounts.session_account(state["adb"], token) if token else None
    if acc is not None:
        check_origin(request)
        sent = request.headers.get("x-csrf-token", "")
        if not sent or not security.safe_equal(sent, acc["csrf_token"]):
            raise HTTPException(403, "Missing or invalid CSRF token")
        accounts.delete_session(state["adb"], token)
    _clear_cookie(response)
    return {"ok": True}


@router.get("/me")
def me(acc: dict = Depends(session_user)):
    profile = accounts.get_profile(state["adb"], acc["id"])
    return {"account": accounts.public_account(acc), "csrf_token": acc["csrf_token"], "redirect": _landing(acc),
            "profile": {"origin": profile["origin"], "country": profile["country"]}}
