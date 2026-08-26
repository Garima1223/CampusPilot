from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.models import User
from app.schemas.user_schema import LoginRequest, SignupRequest
from app.auth.auth import (
    hash_password, verify_password, create_access_token,
    check_lockout, register_failed_attempt, bump_attempt_count, clear_attempts, LOCKOUT_SECONDS,
)
from app.common import log_audit

router = APIRouter(prefix="/auth", tags=["auth"])

ROLE_LABELS = {"student": "Student", "teacher": "Faculty", "admin": "Admin"}


@router.post("/login")
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """
    Mirrors the frontend's api.auth.login(email, password, role) contract:
      - 5 failed attempts on an email locks it out for 45s (server-side now,
        not just client-side state that a page refresh would reset).
      - Wrong password and unknown email return the identical message, so a
        caller can't enumerate which accounts exist.
      - `role` is the portal selected on the login form; if the account's
        real role doesn't match, the login is rejected even though the
        password was correct.
    """
    email_key = credentials.email.strip().lower()
    check_lockout(email_key)

    user = db.query(User).filter(User.email.ilike(email_key)).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        register_failed_attempt(email_key)  # always raises

    if user.status != "active":
        raise HTTPException(status_code=403, detail="This account has been deactivated. Contact your campus admin.")

    if credentials.role and user.role != credentials.role:
        # bump_attempt_count() only counts the attempt — it does NOT raise —
        # so this specific, more useful message actually reaches the caller
        # instead of being replaced by the generic "wrong password" one.
        if bump_attempt_count(email_key):
            raise HTTPException(status_code=429, detail=f"Too many failed attempts. This account is locked for {LOCKOUT_SECONDS}s.")
        raise HTTPException(
            status_code=403,
            detail=f"This account is registered as {ROLE_LABELS.get(user.role, user.role)}, "
                   f"not {ROLE_LABELS.get(credentials.role, credentials.role)}. Switch portals above and try again.",
        )

    clear_attempts(email_key)
    token = create_access_token({"sub": str(user.id), "role": user.role, "name": user.name})
    return {"token": token, "user": user.to_dict()}


@router.post("/signup")
def signup(record: SignupRequest, db: Session = Depends(get_db)):
    """
    Self-service signup is deliberately limited to Student / Faculty. Admin
    accounts are a privileged escalation and can only be created by an
    existing admin from the Users & Roles console (POST /admin/users) —
    never by anyone signing themselves up here.
    """
    if record.role == "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin accounts can't be self-registered. Ask an existing campus admin to create your account from Users & Roles.",
        )
    if record.role not in ("student", "teacher"):
        raise HTTPException(status_code=400, detail="Select a valid portal to sign up for.")
    if db.query(User).filter(User.email.ilike(record.email.strip().lower())).first():
        raise HTTPException(status_code=400, detail="An account with that email already exists.")

    user = User(
        name=record.name, email=record.email, password_hash=hash_password(record.password),
        role=record.role, id_label=record.id_label, status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_audit(db, actor=user.name, actor_role=user.role, action="Account created", detail=f"Signed up as {user.role}")

    token = create_access_token({"sub": str(user.id), "role": user.role, "name": user.name})
    return {"token": token, "user": user.to_dict()}
