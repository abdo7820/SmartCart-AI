import hashlib
import hmac
import re
import secrets
import threading
import time
from collections import defaultdict, deque

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from email_validator import EmailNotValidError, validate_email

from . import config

_hasher = PasswordHasher()
_DUMMY_HASH = _hasher.hash("not-a-real-password-for-timing")
COMMON_PASSWORDS = {
    "password", "password1", "password12", "password123", "passw0rd", "qwerty123", "qwertyuiop", "letmein123", "iloveyou1", "admin12345",
    "welcome123", "123456789", "1234567890", "12345678910", "abc123456", "changeme123", "smartcart123",
}


def normalize_email(raw):
    try:
        return validate_email(raw.strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError as e:
        raise ValueError(str(e))


def password_problems(password, email=None, full_name=None):
    problems = []
    if len(password) < 10:
        problems.append("at least 10 characters")
    if len(password) > 128:
        problems.append("at most 128 characters")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        problems.append("both letters and digits")
    if password.lower() in COMMON_PASSWORDS:
        problems.append("not a commonly used password")
    low = password.lower()
    if email and len(email.split("@")[0]) >= 4 and email.split("@")[0].lower() in low:
        problems.append("must not contain the part of your email before the @")
    if full_name:
        for part in re.split(r"\s+", full_name.lower()):
            if len(part) >= 4 and part in low:
                problems.append("must not contain your name")
                break
    return problems


def hash_password(password):
    return _hasher.hash(password)


def verify_password(password, stored):
    try:
        return _hasher.verify(stored, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def burn_verification_time(password):
    verify_password(password, _DUMMY_HASH)


def needs_rehash(stored):
    try:
        return _hasher.check_needs_rehash(stored)
    except InvalidHashError:
        return False


def new_token():
    return secrets.token_urlsafe(32)


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def safe_equal(a, b):
    return hmac.compare_digest(a.encode(), b.encode())


class RateLimiter:
    def __init__(self):
        self.lock = threading.Lock()
        self.hits = defaultdict(deque)

    def reset(self):
        with self.lock:
            self.hits.clear()

    def reset_key(self, key):
        """Clear one limiter bucket after a verified successful action."""
        with self.lock:
            self.hits.pop(key, None)

    def allow(self, key, limit, window_s):
        if not config.RATE_LIMIT_ENABLED:
            return True
        now = time.monotonic()
        with self.lock:
            q = self.hits[key]
            while q and now - q[0] > window_s:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True


limiter = RateLimiter()
