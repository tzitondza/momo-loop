"""JWT authentication and role-based access helpers."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .database import get_db  # loads .env via database module
from .models import ROLE_PERMISSIONS, User

SECRET_KEY = os.getenv("MOMO_LOOP_SECRET", "momo-loop-hackathon-dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 12

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, role: str, extra: dict | None = None) -> str:
    payload = {
        "sub": subject,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = data.get("sub")
        if not email:
            raise credentials_exc
    except JWTError as exc:
        raise credentials_exc from exc

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise credentials_exc
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(permission: str):
    def checker(user: CurrentUser) -> User:
        allowed = ROLE_PERMISSIONS.get(user.role, set())
        if permission not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' cannot access '{permission}'",
            )
        return user

    return checker
