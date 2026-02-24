from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import get_current_user, get_db

router = APIRouter(prefix="/messages", tags=["messages"])


class MessageCreateBody(BaseModel):
    content: str


def _get_or_create_global_room(db: Session) -> models.MessageRoom:
    room = db.query(models.MessageRoom).filter(models.MessageRoom.type == "global").first()
    if room:
        return room

    room = models.MessageRoom(type="global")
    db.add(room)
    db.flush()
    return room


def _ensure_room_access(db: Session, room_id: int, user_id: int) -> models.MessageRoom:
    room = db.query(models.MessageRoom).filter(models.MessageRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.type == "global":
        return room

    is_member = (
        db.query(models.ChatRoomMember)
        .filter(models.ChatRoomMember.room_id == room_id, models.ChatRoomMember.user_id == user_id)
        .first()
    )
    if not is_member:
        raise HTTPException(status_code=403, detail="Not allowed to access this room")
    return room


@router.get("/global", response_model=schemas.MessageRoomOut)
def get_global_room(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _ = current_user
    room = _get_or_create_global_room(db)
    db.commit()
    db.refresh(room)
    return room


@router.get("/users", response_model=list[schemas.MessageUserOut])
def list_dm_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.User)
        .filter(models.User.id != current_user.id, models.User.is_active.is_(True))
        .order_by(func.lower(models.User.name).asc(), func.lower(models.User.email).asc())
        .all()
    )


@router.post("/dm/{user_id}", response_model=schemas.MessageRoomOut)
def get_or_create_dm_room(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot create a DM room with yourself")

    other_user = db.query(models.User).filter(models.User.id == user_id, models.User.is_active.is_(True)).first()
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")

    candidate_rooms = (
        db.query(models.MessageRoom)
        .join(models.ChatRoomMember, models.ChatRoomMember.room_id == models.MessageRoom.id)
        .filter(models.MessageRoom.type == "dm", models.ChatRoomMember.user_id.in_([current_user.id, user_id]))
        .group_by(models.MessageRoom.id)
        .having(func.count(models.ChatRoomMember.user_id.distinct()) == 2)
        .all()
    )

    for room in candidate_rooms:
        member_count = (
            db.query(func.count(models.ChatRoomMember.user_id))
            .filter(models.ChatRoomMember.room_id == room.id)
            .scalar()
        )
        if member_count == 2:
            return room

    room = models.MessageRoom(type="dm")
    db.add(room)
    db.flush()

    db.add(models.ChatRoomMember(room_id=room.id, user_id=current_user.id))
    db.add(models.ChatRoomMember(room_id=room.id, user_id=user_id))
    db.commit()
    db.refresh(room)
    return room


@router.get("/rooms/{room_id}", response_model=list[schemas.MessageOut])
def list_room_messages(
    room_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    before: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _ensure_room_access(db, room_id=room_id, user_id=current_user.id)

    query = (
        db.query(models.Message)
        .join(models.User, models.User.id == models.Message.sender_user_id)
        .filter(models.Message.room_id == room_id)
    )
    if before:
        query = query.filter(models.Message.created_at < before)

    rows = query.order_by(models.Message.created_at.desc(), models.Message.id.desc()).limit(limit).all()
    return list(reversed(rows))


@router.post("/rooms/{room_id}", response_model=schemas.MessageOut)
def send_room_message(
    room_id: int,
    payload: MessageCreateBody,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _ensure_room_access(db, room_id=room_id, user_id=current_user.id)

    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message content cannot be empty")

    message = models.Message(room_id=room_id, sender_user_id=current_user.id, content=content)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message
