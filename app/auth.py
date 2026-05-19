import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.models import CurrentUser

SECRET = os.getenv("JWT_SECRET", "change-me")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

_bearer = HTTPBearer()


def create_token(name: str, role: str) -> str:
    payload = {
        "name": name,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)

def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> CurrentUser:
    try:
        payload = jwt.decode(credentials.credentials, SECRET, algorithms=[ALGORITHM])
        name: str = payload.get("name")
        role: str = payload.get("role")
        if not name or not role:
            raise ValueError
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return CurrentUser(name=name, role=role)

def require_role(*roles: str):
    def check(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user
    return check
