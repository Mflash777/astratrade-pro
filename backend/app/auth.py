"""JWT + API-key authentication, password hashing (PBKDF2), role checks."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import get_settings
from .db import User, get_db

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
ALGO = "HS256"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return f"pbkdf2$200000${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except ValueError:
        return False


def create_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": str(user.id), "email": user.email, "role": user.role, "tier": user.subscription_tier, "exp": exp},
                      settings.secret_key, algorithm=ALGO)


def generate_api_key() -> str:
    return "atp_" + secrets.token_hex(24)


def get_current_user(token: str | None = Depends(oauth2_scheme), x_api_key: str | None = Header(default=None),
                     db: Session = Depends(get_db)) -> User:
    user: User | None = None
    if token:
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[ALGO])
            user = db.get(User, int(payload["sub"]))
        except (jwt.PyJWTError, KeyError, ValueError):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from None
    elif x_api_key:
        user = db.query(User).filter(User.api_key == x_api_key).first()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin role required")
    return user


def require_pro(user: User = Depends(get_current_user)) -> User:
    if user.subscription_tier not in ("pro", "team") and user.role != "admin":
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Pro subscription required for this feature")
    return user
