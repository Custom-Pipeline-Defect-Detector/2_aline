from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from app import models
from app.deps import get_db
from app.routers.ai_chat import _extract_memories, router
from app.auth import create_access_token


def _init_db() -> sessionmaker:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    email VARCHAR NOT NULL UNIQUE,
                    name VARCHAR NOT NULL,
                    password_hash VARCHAR NOT NULL,
                    is_active BOOLEAN NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE chat_sessions (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title VARCHAR,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE chat_messages (
                    id INTEGER PRIMARY KEY,
                    session_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    role VARCHAR NOT NULL,
                    content TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE user_memories (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    type VARCHAR NOT NULL,
                    key VARCHAR,
                    content TEXT NOT NULL,
                    relevance FLOAT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        )
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def _seed_users(db: Session) -> tuple[models.User, models.User]:
    user_a = models.User(email="a@example.com", name="User A", password_hash="x", is_active=True)
    user_b = models.User(email="b@example.com", name="User B", password_hash="x", is_active=True)
    db.add_all([user_a, user_b])
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)
    return user_a, user_b


def _make_client(local_session: sessionmaker) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api")

    def _override_db():
        db = local_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    return TestClient(app)


def test_session_and_memory_user_isolation():
    local_session = _init_db()
    client = _make_client(local_session)

    with local_session() as db:
        user_a, user_b = _seed_users(db)

    token_a = create_access_token(subject=user_a.email)
    token_b = create_access_token(subject=user_b.email)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    res_a = client.post("/api/ai/sessions", headers=headers_a, json={"title": "A session"})
    res_b = client.post("/api/ai/sessions", headers=headers_b, json={"title": "B session"})
    assert res_a.status_code == 200
    assert res_b.status_code == 200
    session_b_id = res_b.json()["id"]

    forbidden_read = client.get(f"/api/ai/sessions/{session_b_id}/messages", headers=headers_a)
    assert forbidden_read.status_code == 404

    with local_session() as db:
        db.add_all(
            [
                models.UserMemory(user_id=user_a.id, type="preference", content="pref A", relevance=0.8),
                models.UserMemory(user_id=user_b.id, type="project", content="proj B", relevance=0.9),
            ]
        )
        db.commit()
        memory_b_id = (
            db.query(models.UserMemory).filter(models.UserMemory.user_id == user_b.id).first().id
        )

    mem_a = client.get("/api/ai/memory", headers=headers_a)
    assert mem_a.status_code == 200
    assert [item["content"] for item in mem_a.json()] == ["pref A"]

    forbidden_delete = client.delete(f"/api/ai/memory/{memory_b_id}", headers=headers_a)
    assert forbidden_delete.status_code == 404


def test_memory_upsert_and_cap(monkeypatch):
    local_session = _init_db()
    with local_session() as db:
        user_a, _ = _seed_users(db)
        db.add(models.UserMemory(user_id=user_a.id, type="goal", content="Keep markdown", relevance=0.4))
        db.commit()

        def fake_chat(messages, temperature=0.0):
            return '{"memories":[' + ",".join(
                ['{"content":"Keep markdown","type":"preference","relevance":0.9}']
                + [f'{{"content":"memory {i}","type":"project","relevance":0.2}}' for i in range(60)]
            ) + ']}'

        monkeypatch.setattr("app.routers.ai_chat._chat", fake_chat)
        changed = _extract_memories(
            db,
            user_id=user_a.id,
            snippet_messages=[models.ChatMessage(role="user", content="hello")],
            assistant_reply="ok",
        )
        assert changed is True
        db.commit()

        memories = (
            db.query(models.UserMemory)
            .filter(models.UserMemory.user_id == user_a.id)
            .order_by(models.UserMemory.relevance.desc(), models.UserMemory.updated_at.desc())
            .all()
        )
        assert len(memories) == 50
        keep_markdown = [m for m in memories if m.content == "Keep markdown"]
        assert len(keep_markdown) == 1
        assert keep_markdown[0].relevance == 0.9
        assert isinstance(keep_markdown[0].updated_at, datetime)
