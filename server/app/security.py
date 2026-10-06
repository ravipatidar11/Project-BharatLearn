from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .db import query

bearer = HTTPBearer(auto_error=False)


def password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def password_matches(password: str, encoded: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), encoded.encode("ascii"))
    except (ValueError, TypeError):
        return False


def sign_token(user_id: Any) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(user_id), "iss": "bharatlearn", "iat": now, "exp": now + timedelta(days=7)},
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )


def require_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict[str, Any]:
    invalid = HTTPException(status_code=401, detail="Your session is invalid. Please sign in again.")
    if not credentials:
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    try:
        claims = jwt.decode(credentials.credentials, os.environ["JWT_SECRET"], algorithms=["HS256"], issuer="bharatlearn")
        user = query("SELECT id,full_name,email,role,city FROM users WHERE id=$1", [claims["sub"]])
    except Exception as exc:
        raise invalid from exc
    if not user:
        raise HTTPException(status_code=401, detail="Your session has expired. Please sign in again.")
    return user[0]


def require_admin(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access is required.")
    return user
