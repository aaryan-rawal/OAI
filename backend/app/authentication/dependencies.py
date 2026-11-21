from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.models import User
from app.authentication.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)

async def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id = decode_access_token(credentials.credentials) if credentials else None
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Valid bearer token required.")
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=401, detail="Account no longer exists.")
    return user

async def organization_owner(user: User = Depends(current_user)) -> User:
    if user.role not in {"organization_owner", "organization_manager", "platform_admin", "admin"}:
        raise HTTPException(status_code=403, detail="Organization management permission required.")
    return user
