from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=80, pattern="^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=6, max_length=128)
    nickname: str = Field(..., min_length=1, max_length=80)
    color: str = Field(default="#ffffff", pattern="^#[0-9a-fA-F]{6}$")


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[int] = None


class MessageCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class MessageResponse(BaseModel):
    id: int
    message: str
    timestamp: Optional[datetime] = None
    nickname: str
    color: str

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    username: str
    nickname: str
    color: str

    class Config:
        from_attributes = True


class UserColorUpdate(BaseModel):
    color: str = Field(..., pattern="^#[0-9a-fA-F]{6}$")


class UserNicknameUpdate(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=80)
