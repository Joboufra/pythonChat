from fastapi import Depends, HTTPException, status, WebSocket, Cookie, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db, async_session
from app.core.security import decode_access_token
from app.models.models import User
from typing import Optional

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    token_cookie: Optional[str] = Cookie(default=None, alias="token"),
    db: AsyncSession = Depends(get_db)
) -> User:
    auth_token = token or token_cookie
    if not auth_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_access_token(auth_token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


async def get_current_user_websocket(websocket: WebSocket) -> User:
    token = websocket.query_params.get("token")
    if not token:
        token = websocket.cookies.get("token")

    if not token or len(token) > 2000:
        await websocket.close(code=4001)
        return None

    payload = decode_access_token(token)
    if payload is None:
        await websocket.close(code=4001)
        return None

    user_id: int = payload.get("sub")
    if user_id is None:
        await websocket.close(code=4001)
        return None

    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()

    if user is None:
        await websocket.close(code=4001)
        return None

    return user
