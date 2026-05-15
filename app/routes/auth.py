from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.dependencies import get_current_user
from app.core.ratelimit import auth_rate_limiter, get_client_ip
from app.models.models import User
from app.schemas.schemas import UserRegister, Token, UserResponse, UserColorUpdate, UserNicknameUpdate
from app.core.config import settings
from pydantic import BaseModel
from datetime import timedelta
import re
import html

router = APIRouter(prefix="/api/auth", tags=["auth"])


def sanitize_input(value: str) -> str:
    return html.escape(value.strip())


def validate_username(username: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9_]{3,80}$', username))


def validate_password_input(password: str) -> bool:
    if len(password) < 6 or len(password) > 128:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    return True


class ConfigResponse(BaseModel):
    allow_registration: bool


class WsTokenResponse(BaseModel):
    ws_token: str


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    return ConfigResponse(allow_registration=settings.ALLOW_REGISTRATION)


@router.get("/ws-token", response_model=WsTokenResponse)
async def get_ws_token(current_user: User = Depends(get_current_user)):
    ws_token = create_access_token(
        data={"sub": str(current_user.id), "type": "ws"},
        expires_delta=timedelta(seconds=60)
    )
    return WsTokenResponse(ws_token=ws_token)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="token", path="/")
    return {"status": "success"}


def validate_password_strength(password: str) -> bool:
    return validate_password_input(password)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    if not settings.ALLOW_REGISTRATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is currently disabled"
        )

    client_ip = get_client_ip(request)
    if auth_rate_limiter.is_rate_limited(f"register:{client_ip}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Try again later."
        )

    if not validate_password_strength(user_data.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters and contain uppercase, lowercase, and numbers"
        )

    if not validate_username(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid username format"
        )

    nickname = sanitize_input(user_data.nickname)
    if len(nickname) < 1 or len(nickname) > 80:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid nickname length"
        )

    result = await db.execute(select(User).where(
        (User.username == user_data.username) | (User.nickname == user_data.nickname)
    ))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or nickname already exists")

    new_user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        nickname=nickname,
        color=user_data.color
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    client_ip = get_client_ip(request)
    if auth_rate_limiter.is_rate_limited(f"login:{client_ip}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later."
        )

    if not validate_username(form_data.username):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if len(form_data.password) > 128:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": str(user.id)})

    response.set_cookie(
        key="token",
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me/color", response_model=UserResponse)
async def update_color(
    color_data: UserColorUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not re.match(r'^#[0-9a-fA-F]{6}$', color_data.color):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid color format"
        )

    old_color = current_user.color
    current_user.color = color_data.color
    await db.commit()
    await db.refresh(current_user)

    if old_color != color_data.color:
        from app.routes.chat import connected_users, user_colors
        user_colors[current_user.id] = color_data.color
        update_event = {
            "type": "user_color_update",
            "user_id": current_user.id,
            "nickname": current_user.nickname,
            "color": color_data.color
        }
        for uid, ws in list(connected_users.items()):
            try:
                await ws.send_json(update_event)
            except Exception:
                connected_users.pop(uid, None)

    return current_user


@router.patch("/me/nickname", response_model=UserResponse)
async def update_nickname(
    nickname_data: UserNicknameUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    nickname = sanitize_input(nickname_data.nickname)
    if len(nickname) < 1 or len(nickname) > 80:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid nickname length"
        )

    result = await db.execute(select(User).where(
        (User.nickname == nickname) & (User.id != current_user.id)
    ))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nickname already exists"
        )

    old_nickname = current_user.nickname
    current_user.nickname = nickname
    await db.commit()
    await db.refresh(current_user)

    if old_nickname != nickname:
        from app.routes.chat import connected_users, user_nicks, user_colors
        user_nicks[current_user.id] = nickname
        update_event = {
            "type": "user_nickname_update",
            "user_id": current_user.id,
            "old_nickname": old_nickname,
            "nickname": nickname,
            "color": user_colors.get(current_user.id, current_user.color)
        }
        for uid, ws in list(connected_users.items()):
            try:
                await ws.send_json(update_event)
            except Exception:
                connected_users.pop(uid, None)

    return current_user
