"""
Auth primitives: password hashing + JWTs + the login lockout guard.

DELIBERATELY DEPENDENCY-MINIMAL. The first version of this file used
python-jose for JWTs and passlib[bcrypt] for password hashing — both are
common choices, but both are also common sources of "it installs fine but
crashes at runtime" on a fresh machine:
  - passlib 1.7.x + a recent bcrypt (>=4.1) hits a well-known crash
    (`AttributeError: module 'bcrypt' has no attribute '__about__'`) because
    passlib probes an attribute bcrypt removed. Pinning around it is
    possible but fragile — it silently breaks again the next time someone
    upgrades bcrypt.
  - python-jose needs a crypto backend and has historically had version
    churn between its `cryptography`-backed and pure-python code paths.

Neither is needed here. Password hashing uses PBKDF2-HMAC-SHA256 from the
Python standard library (`hashlib`) — no C/Rust extension, nothing that can
fail to build, and it's what Django used as its default hasher for years.
JWTs use PyJWT, which has no required dependencies for HS256 (what this app
uses). Fewer moving parts = fewer ways for `pip install` to leave you with a
backend that doesn't run.
"""
import os
import time
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# In production, set SECRET_KEY via an environment variable. If it's not
# set, generate a random one at startup rather than falling back to a fixed
# placeholder — a hardcoded fallback secret checked into source is a real
# vulnerability (anyone who reads the code can forge tokens), and a fixed
# string this short also triggers PyJWT's "HMAC key too short" warning.
# Trade-off: without SECRET_KEY set, all logged-in sessions are invalidated
# on every server restart — fine for dev, so set SECRET_KEY for anything
# that needs sessions to survive a restart.
SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

PBKDF2_ITERATIONS = 260_000  # OWASP-recommended floor for PBKDF2-HMAC-SHA256 as of 2023+


# --------------------------------------------------------------- Passwords
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    try:
        scheme, iterations, salt, hex_digest = stored_hash.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(digest.hex(), hex_digest)
    except (ValueError, AttributeError):
        return False


# -------------------------------------------------------------------- JWTs
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


security_scheme = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)):
    token = credentials.credentials
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        role = payload.get("role")
        name = payload.get("name")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"user_id": int(user_id), "role": role, "name": name}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_role(allowed_roles: list):
    """allowed_roles are lowercase to match the frontend's role keys: student/teacher/admin."""
    def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Not authorized for this action")
        return current_user
    return role_checker


# ---------------------------------------------------------------------------
# Brute-force login guard — server-side version of the frontend mock's
# attemptState()/MAX_LOGIN_ATTEMPTS/LOCKOUT_MS policy: 5 wrong attempts on
# an email locks it out for 45s.
#
# NOTE: this in-memory dict resets on server restart and isn't shared across
# multiple worker processes. Fine for a single-process dev/demo deployment;
# a real multi-worker production deployment should move this into Redis (or
# similar) keyed by email.
# ---------------------------------------------------------------------------
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 45
_login_attempts = {}  # email -> {"count": int, "locked_until": epoch_seconds}

def check_lockout(email_key: str):
    state = _login_attempts.get(email_key)
    if state and state["locked_until"] > time.time():
        secs = int(state["locked_until"] - time.time()) + 1
        raise HTTPException(status_code=429, detail=f"Too many failed attempts. Try again in {secs}s.")

def bump_attempt_count(email_key: str) -> bool:
    """
    Counts one failed attempt against an email WITHOUT raising, so callers
    that need a specific error message (e.g. the role-mismatch case in
    auth_router.py) can bump the counter and then raise their own
    HTTPException. Returns True if this attempt just crossed the lockout
    threshold (caller should raise 429 instead of its usual error).
    """
    state = _login_attempts.setdefault(email_key, {"count": 0, "locked_until": 0})
    state["count"] += 1
    if state["count"] >= MAX_LOGIN_ATTEMPTS:
        state["locked_until"] = time.time() + LOCKOUT_SECONDS
        state["count"] = 0
        return True
    return False

def register_failed_attempt(email_key: str):
    """
    For the plain 'wrong email or password' case: always raises — 429 if
    this attempt just crossed the lockout threshold, else a generic 401
    (deliberately identical whether the email didn't exist or the password
    was wrong, so a caller can't enumerate which accounts exist).
    """
    if bump_attempt_count(email_key):
        raise HTTPException(status_code=429, detail=f"Too many failed attempts. This account is locked for {LOCKOUT_SECONDS}s.")
    raise HTTPException(status_code=401, detail="Incorrect email or password.")

def clear_attempts(email_key: str):
    _login_attempts.pop(email_key, None)
