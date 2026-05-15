from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text
from sqlalchemy.orm import selectinload
from app.core.database import get_db, async_session
from app.core.dependencies import get_current_user_websocket
from app.core.ratelimit import message_rate_limiter
from app.models.models import User, Message
from app.schemas.schemas import MessageResponse
from typing import List
import json
import html
import re

router = APIRouter(prefix="/api/chat", tags=["chat"])

connected_users: dict[int, WebSocket] = {}
user_colors: dict[int, str] = {}
user_nicks: dict[int, str] = {}


@router.get("/online-count")
async def get_online_count():
    return {"count": len(connected_users)}


@router.get("/messages", response_model=List[MessageResponse])
async def get_messages(limit: int = Query(50, le=200), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Message)
        .options(selectinload(Message.user))
        .order_by(Message.timestamp.desc())
        .limit(limit)
    )
    messages = result.scalars().all()

    messages_with_user = []
    for msg in messages:
        messages_with_user.append(MessageResponse(
            id=msg.id,
            message=msg.message,
            timestamp=msg.timestamp,
            nickname=msg.user.nickname,
            color=msg.user.color
        ))

    return list(reversed(messages_with_user))


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    user = await get_current_user_websocket(websocket)
    if not user:
        return

    await websocket.accept()
    connected_users[user.id] = websocket
    user_colors[user.id] = user.color
    user_nicks[user.id] = user.nickname

    online_data = {"type": "online_update", "count": len(connected_users)}
    for uid, ws in list(connected_users.items()):
        try:
            await ws.send_json(online_data)
        except Exception:
            connected_users.pop(uid, None)

    async with async_session() as db:
        try:
            while True:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                message_text = message_data.get("message", "").strip()

                if not message_text:
                    continue

                if message_rate_limiter.is_rate_limited(f"msg:{user.id}"):
                    await websocket.send_json({"error": "Rate limit exceeded. Slow down."})
                    continue

                if len(message_text) > 2000:
                    await websocket.send_json({"error": "Message too long"})
                    continue

                new_message = Message(message=message_text, user_id=user.id)
                db.add(new_message)
                await db.commit()
                await db.refresh(new_message)

                message_response = {
                    "id": new_message.id,
                    "message": new_message.message,
                    "timestamp": new_message.timestamp.isoformat() if new_message.timestamp else None,
                    "nickname": user_nicks.get(user.id, user.nickname),
                    "color": user_colors.get(user.id, user.color)
                }

                for uid, ws in list(connected_users.items()):
                    try:
                        await ws.send_json(message_response)
                    except Exception:
                        connected_users.pop(uid, None)

        except WebSocketDisconnect:
            connected_users.pop(user.id, None)
            user_colors.pop(user.id, None)
            user_nicks.pop(user.id, None)
            online_data = {"type": "online_update", "count": len(connected_users)}
            for uid, ws in list(connected_users.items()):
                try:
                    await ws.send_json(online_data)
                except Exception:
                    connected_users.pop(uid, None)


@router.post("/clear")
async def clear_messages(db: AsyncSession = Depends(get_db)):
    await db.execute(text("DELETE FROM chat.messages"))
    await db.commit()
    return {"status": "success", "message": "All messages cleared"}
