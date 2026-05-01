"""JWT authentication and RBAC authorization for CanvasML Studio."""

from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import wraps
from typing import Any, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import settings

security = HTTPBearer()


# ── RBAC Role Definitions ────────────────────────────────


class Role(str, Enum):
    """Platform roles matching the database seed in 001_initial_schema."""

    PLATFORM_ADMIN = "PlatformAdmin"
    DATA_ENGINEER = "DataEngineer"
    DATA_SCIENTIST = "DataScientist"
    RISK_OFFICER = "RiskOfficer"
    BUSINESS_USER = "BusinessUser"
    AUDITOR = "Auditor"


# Role hierarchy — higher roles inherit lower role permissions
ROLE_HIERARCHY: dict[Role, set[Role]] = {
    Role.PLATFORM_ADMIN: {
        Role.PLATFORM_ADMIN,
        Role.DATA_ENGINEER,
        Role.DATA_SCIENTIST,
        Role.RISK_OFFICER,
        Role.BUSINESS_USER,
        Role.AUDITOR,
    },
    Role.DATA_ENGINEER: {Role.DATA_ENGINEER},
    Role.DATA_SCIENTIST: {Role.DATA_SCIENTIST},
    Role.RISK_OFFICER: {Role.RISK_OFFICER, Role.AUDITOR},
    Role.BUSINESS_USER: {Role.BUSINESS_USER},
    Role.AUDITOR: {Role.AUDITOR},
}


# ── Token Models ─────────────────────────────────────────


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # user_id
    email: str
    role: str
    exp: datetime


class CurrentUser(BaseModel):
    """Authenticated user context available in request handlers."""

    user_id: str
    email: str
    role: Role


# ── Token Operations ─────────────────────────────────────


def create_access_token(user_id: str, email: str, role: str) -> str:
    """Create a signed JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> TokenPayload:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return TokenPayload(**payload)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# ── FastAPI Dependencies ─────────────────────────────────


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    """Extract and validate the current user from the Authorization header."""
    token_data = decode_token(credentials.credentials)

    if token_data.exp < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        role = Role(token_data.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unknown role: {token_data.role}",
        )

    return CurrentUser(user_id=token_data.sub, email=token_data.email, role=role)


def require_roles(*allowed_roles: Role) -> Callable[..., Any]:
    """Dependency factory — restrict endpoint to specific roles.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_roles(Role.PLATFORM_ADMIN))])
        async def admin_endpoint(): ...
    """

    async def _check_role(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        effective_roles = ROLE_HIERARCHY.get(user.role, {user.role})
        if not effective_roles.intersection(set(allowed_roles)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role.value}' does not have access. Required: {[r.value for r in allowed_roles]}",
            )
        return user

    return _check_role
