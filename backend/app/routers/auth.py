from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..audit import audit
from ..auth import (create_token, generate_api_key, get_current_user, hash_password, require_admin,
                    verify_password)
from ..db import AuditLog, User, get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    subscription_tier: str
    api_key: str | None = None


def _out(u: User) -> UserOut:
    return UserOut(id=u.id, email=u.email, role=u.role, subscription_tier=u.subscription_tier, api_key=u.api_key)


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)) -> UserOut:
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if db.query(User).filter(User.email == body.email.lower()).first():
        raise HTTPException(409, "Email already registered")
    u = User(email=body.email.lower(), password_hash=hash_password(body.password))
    db.add(u)
    db.commit()
    db.refresh(u)
    audit(db, "user.register", f"user:{u.id}", user_id=u.id, request=request)
    return _out(u)


@router.post("/login")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> dict:
    u = db.query(User).filter(User.email == form.username.lower()).first()
    if not u or not verify_password(form.password, u.password_hash):
        audit(db, "user.login_failed", f"email:{form.username}", request=request)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    audit(db, "user.login", f"user:{u.id}", user_id=u.id, request=request)
    return {"access_token": create_token(u), "token_type": "bearer", "user": _out(u).model_dump()}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return _out(user)


@router.post("/api-key", response_model=UserOut)
def rotate_api_key(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserOut:
    if user.subscription_tier not in ("pro", "team") and user.role != "admin":
        raise HTTPException(402, "API access requires a Pro subscription")
    user.api_key = generate_api_key()
    db.commit()
    audit(db, "user.api_key_rotated", f"user:{user.id}", user_id=user.id, request=request)
    return _out(user)


@router.post("/admin/set-tier/{user_id}", response_model=UserOut)
def set_tier(user_id: int, tier: str, request: Request, admin: User = Depends(require_admin),
             db: Session = Depends(get_db)) -> UserOut:
    if tier not in ("free", "pro", "team"):
        raise HTTPException(400, "tier must be free, pro or team")
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    u.subscription_tier = tier
    db.commit()
    audit(db, "admin.set_tier", f"user:{u.id}", {"tier": tier}, user_id=admin.id, request=request)
    return _out(u)


@router.get("/admin/audit")
def list_audit(limit: int = 100, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(limit, 500)).all()
    return [{"id": r.id, "user_id": r.user_id, "action": r.action, "resource": r.resource, "detail": r.detail,
             "ip": r.ip, "created_at": r.created_at.isoformat()} for r in rows]
