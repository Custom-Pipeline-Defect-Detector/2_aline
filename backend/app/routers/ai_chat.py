from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import get_db, get_current_user
from app.ollama_client import _chat

router = APIRouter(prefix="/ai", tags=["ai"])

SYSTEM_PROMPT = (
    "You are an AI assistant embedded in an engineering inbox. "
    "Follow user instructions, be concise, and avoid unsafe/speculative actions. "
    "Never ask for secrets and never include sensitive credentials in output."
)
MEMORY_LIMIT = 50
MEMORY_FETCH_LIMIT = 8
RECENT_CHAT_LIMIT = 12
MEMORY_TURNS_FOR_EXTRACTION = 12


def _normalize_memory_content(content: str) -> str:
    return " ".join((content or "").strip().split())


def _build_memory_block(memories: list[models.UserMemory]) -> str:
    if not memories:
        return "- (none)"
    lines = [f"- [{memory.type}] {memory.content} (relevance={memory.relevance:.2f})" for memory in memories]
    return "\n".join(lines)


def _parse_memory_candidates(raw: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []

    memories = parsed.get("memories") if isinstance(parsed, dict) else None
    if not isinstance(memories, list):
        return []

    accepted: list[dict[str, Any]] = []
    for item in memories:
        if not isinstance(item, dict):
            continue
        content = _normalize_memory_content(str(item.get("content", "")))
        if not content:
            continue
        memory_type = str(item.get("type") or "general")[:64]
        try:
            relevance = float(item.get("relevance", 0.5))
        except (TypeError, ValueError):
            relevance = 0.5
        relevance = max(0.0, min(1.0, relevance))
        accepted.append({"content": content, "type": memory_type, "relevance": relevance})
    return accepted


def _extract_memories(db: Session, user_id: int, snippet_messages: list[models.ChatMessage], assistant_reply: str) -> bool:
    if not snippet_messages and not assistant_reply.strip():
        return False

    convo_lines = [f"{msg.role}: {msg.content}" for msg in snippet_messages]
    convo_lines.append(f"assistant: {assistant_reply}")
    extraction_prompt = (
        "Extract durable memory candidates from the conversation.\n"
        "Only include stable user preferences, long-running goals/tasks, recurring constraints, and stable facts.\n"
        "Do NOT include transient chit-chat, one-off requests, secrets, passwords, or private credentials.\n"
        "Return strict JSON only with this shape: "
        '{"memories":[{"content":"...","type":"preference|project|role|constraint|goal|general","relevance":0.0}]}'
    )

    raw = _chat(
        [
            {"role": "system", "content": extraction_prompt},
            {"role": "user", "content": "\n".join(convo_lines[-(MEMORY_TURNS_FOR_EXTRACTION + 1) :])},
        ],
        temperature=0.0,
    )

    candidates = _parse_memory_candidates(raw)
    if not candidates:
        return False

    changed = False
    for candidate in candidates:
        existing = (
            db.query(models.UserMemory)
            .filter(models.UserMemory.user_id == user_id, models.UserMemory.content == candidate["content"])
            .first()
        )
        if existing:
            existing.relevance = max(existing.relevance, candidate["relevance"])
            existing.type = candidate["type"]
            existing.updated_at = datetime.utcnow()
            changed = True
            continue

        db.add(
            models.UserMemory(
                user_id=user_id,
                type=candidate["type"],
                content=candidate["content"],
                relevance=candidate["relevance"],
            )
        )
        changed = True

    db.flush()
    total_memories = db.query(models.UserMemory).filter(models.UserMemory.user_id == user_id).count()
    overflow = max(0, total_memories - MEMORY_LIMIT)
    memory_ids_to_delete = []
    if overflow:
        memory_ids_to_delete = [
            row.id
            for row in db.query(models.UserMemory)
            .filter(models.UserMemory.user_id == user_id)
            .order_by(models.UserMemory.relevance.asc(), models.UserMemory.updated_at.asc())
            .limit(overflow)
            .all()
        ]
    if memory_ids_to_delete:
        db.query(models.UserMemory).filter(models.UserMemory.id.in_(memory_ids_to_delete)).delete(
            synchronize_session=False
        )
        changed = True

    return changed


def _get_user_session_or_404(db: Session, session_id: int, user_id: int) -> models.ChatSession:
    session = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.id == session_id, models.ChatSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/sessions", response_model=schemas.ChatSessionOut)
def create_session(
    payload: schemas.ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = models.ChatSession(user_id=current_user.id, title=(payload.title or None))
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions", response_model=list[schemas.ChatSessionOut])
def list_sessions(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return (
        db.query(models.ChatSession)
        .filter(models.ChatSession.user_id == current_user.id)
        .order_by(models.ChatSession.updated_at.desc(), models.ChatSession.id.desc())
        .all()
    )


@router.get("/sessions/{session_id}/messages", response_model=list[schemas.ChatMessageOut])
def list_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_user_session_or_404(db, session_id=session_id, user_id=current_user.id)
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session_id, models.ChatMessage.user_id == current_user.id)
        .order_by(models.ChatMessage.created_at.asc(), models.ChatMessage.id.asc())
        .all()
    )


@router.post("/sessions/{session_id}/messages", response_model=schemas.ChatReplyOut)
def send_message(
    session_id: int,
    payload: schemas.ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = _get_user_session_or_404(db, session_id=session_id, user_id=current_user.id)
    content = payload.message.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    user_msg = models.ChatMessage(session_id=session.id, user_id=current_user.id, role="user", content=content)
    db.add(user_msg)
    db.flush()

    memories = (
        db.query(models.UserMemory)
        .filter(models.UserMemory.user_id == current_user.id)
        .order_by(models.UserMemory.relevance.desc(), models.UserMemory.updated_at.desc())
        .limit(MEMORY_FETCH_LIMIT)
        .all()
    )

    recent_messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session.id, models.ChatMessage.user_id == current_user.id)
        .order_by(models.ChatMessage.created_at.desc(), models.ChatMessage.id.desc())
        .limit(RECENT_CHAT_LIMIT)
        .all()
    )
    recent_messages = list(reversed(recent_messages))

    context_json = json.dumps(payload.context or {}, ensure_ascii=False)
    model_messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": (
                "User durable memory:\n"
                f"{_build_memory_block(memories)}\n\n"
                f"Optional UI context JSON:\n{context_json}"
            ),
        },
    ]
    model_messages.extend(
        {"role": msg.role if msg.role in {"system", "assistant", "user"} else "user", "content": msg.content}
        for msg in recent_messages
    )

    reply = _chat(model_messages, temperature=0.2).strip()
    assistant_msg = models.ChatMessage(session_id=session.id, user_id=current_user.id, role="assistant", content=reply)
    db.add(assistant_msg)
    session.updated_at = datetime.utcnow()

    extraction_source = recent_messages[-MEMORY_TURNS_FOR_EXTRACTION:]
    memory_updated = _extract_memories(db, user_id=current_user.id, snippet_messages=extraction_source, assistant_reply=reply)

    db.commit()
    return schemas.ChatReplyOut(reply=reply, memory_updated=memory_updated)


@router.get("/memory", response_model=list[schemas.UserMemoryOut])
def list_memory(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return (
        db.query(models.UserMemory)
        .filter(models.UserMemory.user_id == current_user.id)
        .order_by(models.UserMemory.relevance.desc(), models.UserMemory.updated_at.desc())
        .all()
    )


@router.delete("/memory/{memory_id}", status_code=204)
def delete_memory(
    memory_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    memory = (
        db.query(models.UserMemory)
        .filter(models.UserMemory.id == memory_id, models.UserMemory.user_id == current_user.id)
        .first()
    )
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    db.delete(memory)
    db.commit()
    return Response(status_code=204)
