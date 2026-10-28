import logging

from fastapi import Depends, HTTPException, Request

from . import accounts, config, security
from .state import state

logger = logging.getLogger(__name__)

UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


def check_origin(request: Request):
    origin = request.headers.get("origin")
    if origin and origin not in config.CORS_ORIGINS:
        raise HTTPException(403, "Origin not allowed")


def client_ip(request: Request):
    return request.client.host if request.client else "unknown"


def session_user(request: Request) -> dict:
    if request.method in UNSAFE:
        check_origin(request)
    acc = accounts.session_account(state["adb"], request.cookies.get(config.SESSION_COOKIE))
    if acc is None:
        raise HTTPException(401, "Not authenticated")
    if request.method in UNSAFE:
        token = request.headers.get("x-csrf-token", "")
        if not token or not security.safe_equal(token, acc["csrf_token"]):
            raise HTTPException(403, "Missing or invalid CSRF token")
    return acc


def admin_user(acc: dict = Depends(session_user)) -> dict:
    if acc["role"] != "admin":
        raise HTTPException(403, "Administrator access required")
    return acc


def profile_of(acc: dict) -> dict:
    return accounts.get_profile(state["adb"], acc["id"])


def rate_limit(key, limit, window_s, message="Too many requests, try again later"):
    if not security.limiter.allow(key, limit, window_s):
        # Do not log the key: login keys contain client/account identifiers.
        logger.warning("rate_limit_blocked scope=%s limit=%d window_s=%d", key[0], limit, window_s)
        raise HTTPException(429, message)
