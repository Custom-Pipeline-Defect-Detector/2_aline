from __future__ import annotations

import json
import queue
import threading
import time
from datetime import datetime
from json import JSONDecodeError, JSONDecoder
from typing import Any, Iterator

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import models, schemas
from app.agent_tools import TOOL_REGISTRY, run_tool
from app.deps import get_current_user, get_db
from app.ollama_client import _chat, _chat_stream

router = APIRouter(prefix="/ai", tags=["ai"])

SYSTEM_PROMPT = (
    "You are an AI assistant embedded in an engineering inbox. "
    "Follow user instructions, be concise, and avoid unsafe/speculative actions. "
    "Never ask for secrets and never include sensitive credentials in output."
)
ACTION_SYSTEM_PROMPT = (
    "You have access to live workspace tools. "
    "When user asks for data, fetch it from tools/database first. "
    "When user asks to create/update/link records, use tool actions (real writes), not pretend text. "
    "Reply in strict JSON with this shape: "
    '{"reply":"...","actions":[{"label":"...","tool":"<allowed_tool>","args":{...}}]}. '
    "If no action is needed, return actions as an empty list. "
    "Do not invent tool names. Use only listed tools."
)

APP_PAGE_MANIFEST = [
    {"name": "Inbox", "route": "/inbox", "module": "ai_review"},
    {"name": "Dashboard", "route": "/dashboard", "module": "overview"},
    {"name": "Projects", "route": "/projects", "module": "project_management"},
    {"name": "Work", "route": "/work", "module": "tasks_worklogs"},
    {"name": "Quality", "route": "/quality", "module": "issues_ncr"},
    {"name": "CRM", "route": "/customers", "module": "customers"},
    {"name": "Messages", "route": "/messages", "module": "chat"},
    {"name": "Documents", "route": "/documents", "module": "document_pipeline"},
    {"name": "Admin", "route": "/status", "module": "system_admin"},
]

MEMORY_LIMIT = 50
MEMORY_FETCH_LIMIT = 8
RECENT_CHAT_LIMIT = 12
MEMORY_TURNS_FOR_EXTRACTION = 12
BACKGROUND_MAX_ROUNDS = 12

READ_ONLY_TOOLS = {
    "get_document_context",
    "get_workspace_snapshot",
    "search_customers",
    "search_projects",
    "search_proposals",
    "search_documents",
    "search_tasks",
    "search_issues",
    "search_ncrs",
    "search_worklogs",
}


def _normalize_memory_content(content: str) -> str:
    return " ".join((content or "").strip().split())


def _extract_json_object(raw: str) -> dict[str, Any] | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except JSONDecodeError:
        pass

    decoder = JSONDecoder()
    start = text.find("{")
    if start == -1:
        return None
    for idx in range(start, len(text)):
        if text[idx] != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[idx:])
            return parsed if isinstance(parsed, dict) else None
        except JSONDecodeError:
            continue
    return None


def _parse_proposed_actions(raw_actions: Any) -> list[schemas.AIProposedAction]:
    if not isinstance(raw_actions, list):
        return []

    actions: list[schemas.AIProposedAction] = []
    for item in raw_actions:
        if not isinstance(item, dict):
            continue
        tool = str(item.get("tool") or "").strip()
        if not tool or tool not in TOOL_REGISTRY:
            continue
        label = str(item.get("label") or f"Run {tool}").strip()[:120]
        args = item.get("args")
        if not isinstance(args, dict):
            args = {}
        actions.append(
            schemas.AIProposedAction(
                label=label,
                method="POST",
                path=f"/ai/tools/{tool}",
                body=args,
            )
        )
    return actions[:6]


def _parse_ai_assistant_output(raw_reply: str) -> tuple[str, list[schemas.AIProposedAction], bool]:
    payload = _extract_json_object(raw_reply)
    if not payload:
        return raw_reply.strip(), [], True

    reply = str(payload.get("reply") or "").strip() or raw_reply.strip()
    actions = _parse_proposed_actions(payload.get("actions"))
    done = bool(payload.get("done", True))
    return reply, actions, done


def _compact_json(data: Any, max_len: int = 1400) -> str:
    text = json.dumps(data, ensure_ascii=False)
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _sanitize_tool_args(tool_name: str, tool_args: dict[str, Any]) -> dict[str, Any]:
    args = dict(tool_args or {})

    if tool_name in {
        "search_customers",
        "search_projects",
        "search_proposals",
        "search_issues",
        "search_ncrs",
    }:
        args.setdefault("query", "")

    if tool_name == "upsert_project":
        args.setdefault("name", "Auto Project")

    if tool_name == "upsert_task":
        if "title" not in args or not str(args.get("title") or "").strip():
            args["title"] = "AI Task"

    return args


def _build_memory_block(memories: list[models.UserMemory]) -> str:
    if not memories:
        return "- (none)"
    return "\n".join(f"- [{m.type}] {m.content} (relevance={m.relevance:.2f})" for m in memories)


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
        accepted.append({"content": content, "type": memory_type, "relevance": max(0.0, min(1.0, relevance))})
    return accepted


def _extract_memories(db: Session, user_id: int, snippet_messages: list[models.ChatMessage], assistant_reply: str) -> bool:
    if not snippet_messages and not assistant_reply.strip():
        return False

    convo_lines = [f"{msg.role}: {msg.content}" for msg in snippet_messages]
    convo_lines.append(f"assistant: {assistant_reply}")
    raw = _chat(
        [
            {
                "role": "system",
                "content": (
                    "Extract durable memory candidates from the conversation.\n"
                    "Only include stable user preferences, long-running goals/tasks, recurring constraints, and stable facts.\n"
                    "Do NOT include transient chit-chat, one-off requests, secrets, passwords, or private credentials.\n"
                    "Return strict JSON only with this shape: "
                    '{"memories":[{"content":"...","type":"preference|project|role|constraint|goal|general","relevance":0.0}]}'
                ),
            },
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
    total = db.query(models.UserMemory).filter(models.UserMemory.user_id == user_id).count()
    overflow = max(0, total - MEMORY_LIMIT)
    if overflow:
        to_delete = [
            row.id
            for row in db.query(models.UserMemory)
            .filter(models.UserMemory.user_id == user_id)
            .order_by(models.UserMemory.relevance.asc(), models.UserMemory.updated_at.asc())
            .limit(overflow)
            .all()
        ]
        if to_delete:
            db.query(models.UserMemory).filter(models.UserMemory.id.in_(to_delete)).delete(synchronize_session=False)
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


def _execute_tool_action(
    *,
    tool_name: str,
    tool_args: dict[str, Any],
    current_user: models.User,
    db: Session,
) -> tuple[bool, dict[str, Any]]:
    if tool_name not in TOOL_REGISTRY:
        return False, {"error": "Tool not allowed"}

    sanitized_args = _sanitize_tool_args(tool_name, tool_args)
    result = run_tool(tool_name, sanitized_args)
    if not result.success:
        return False, result.data

    db.add(
        models.AuditEvent(
            actor_user_id=current_user.id,
            entity_table="ai_tools",
            entity_id=0,
            action=f"execute:{tool_name}",
            payload_json={"args": sanitized_args, "result": result.data},
        )
    )
    db.commit()
    return True, result.data


def _build_prefetch_actions(payload: schemas.ChatMessageCreate) -> list[schemas.AIProposedAction]:
    text = (payload.message or "").strip().lower()
    actions: list[schemas.AIProposedAction] = [
        schemas.AIProposedAction(
            label="Fetch workspace snapshot",
            method="POST",
            path="/ai/tools/get_workspace_snapshot",
            body={"limit": 8},
        )
    ]

    if any(token in text for token in ["task", "tasks", "work"]):
        actions.append(
            schemas.AIProposedAction(
                label="Search tasks",
                method="POST",
                path="/ai/tools/search_tasks",
                body={"limit": 12},
            )
        )
    if any(token in text for token in ["project", "projects"]):
        actions.append(
            schemas.AIProposedAction(
                label="Search projects",
                method="POST",
                path="/ai/tools/search_projects",
                body={"query": ""},
            )
        )
    if any(token in text for token in ["customer", "crm", "client"]):
        actions.append(
            schemas.AIProposedAction(
                label="Search customers",
                method="POST",
                path="/ai/tools/search_customers",
                body={"query": ""},
            )
        )
    if any(token in text for token in ["document", "documents", "file", "pdf"]):
        actions.append(
            schemas.AIProposedAction(
                label="Search documents",
                method="POST",
                path="/ai/tools/search_documents",
                body={"limit": 12},
            )
        )
    if any(token in text for token in ["issue", "issues", "quality"]):
        actions.append(
            schemas.AIProposedAction(
                label="Search issues",
                method="POST",
                path="/ai/tools/search_issues",
                body={"query": ""},
            )
        )
    if any(token in text for token in ["ncr", "nonconformance", "corrective"]):
        actions.append(
            schemas.AIProposedAction(
                label="Search NCRs",
                method="POST",
                path="/ai/tools/search_ncrs",
                body={"query": ""},
            )
        )
    if any(token in text for token in ["proposal", "proposals", "approve", "reject", "pending"]):
        actions.append(
            schemas.AIProposedAction(
                label="Search proposals",
                method="POST",
                path="/ai/tools/search_proposals",
                body={"query": "", "status": "pending" if "pending" in text else None},
            )
        )

    dedup: dict[str, schemas.AIProposedAction] = {}
    for action in actions:
        dedup[action.path] = action
    return list(dedup.values())[:6]


def _build_bootstrap_actions(payload: schemas.ChatMessageCreate) -> list[schemas.AIProposedAction]:
    text = (payload.message or "").strip().lower()
    if not text:
        return []

    actions: list[schemas.AIProposedAction] = []
    if any(token in text for token in ["all", "everything", "overview", "summary", "database", "workspace", "dashboard"]):
        actions.append(
            schemas.AIProposedAction(
                label="Fetch workspace snapshot",
                method="POST",
                path="/ai/tools/get_workspace_snapshot",
                body={"limit": 10},
            )
        )
    if any(token in text for token in ["approve all", "auto approve", "clear pending"]):
        actions.append(
            schemas.AIProposedAction(
                label="Auto-approve pending proposals",
                method="POST",
                path="/ai/tools/auto_approve_pending_proposals",
                body={"limit": 500},
            )
        )

    dedup: dict[str, schemas.AIProposedAction] = {}
    for action in actions:
        dedup[action.path] = action
    return list(dedup.values())[:5]


def _build_model_messages(
    *,
    payload: schemas.ChatMessageCreate,
    memories: list[models.UserMemory],
    recent_messages: list[models.ChatMessage],
    live_context_block: str,
) -> list[dict[str, str]]:
    context_json = json.dumps(payload.context or {}, ensure_ascii=False)
    model_messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": ACTION_SYSTEM_PROMPT},
        {
            "role": "system",
            "content": (
                "You can continue multi-step execution in iterative rounds until goal is complete. "
                "Set done=false when more tool actions are required, done=true when finished."
            ),
        },
        {
            "role": "system",
            "content": f"Application pages/modules available to manage:\n{json.dumps(APP_PAGE_MANIFEST, ensure_ascii=False)}",
        },
        {
            "role": "system",
            "content": "Allowed tools for action proposals:\n" + "\n".join(f"- {name}" for name in sorted(TOOL_REGISTRY.keys())),
        },
        {
            "role": "system",
            "content": (
                "User durable memory:\n"
                f"{_build_memory_block(memories)}\n\n"
                f"Optional UI context JSON:\n{context_json}\n\n"
                f"Live workspace/tool context:\n{live_context_block}"
            ),
        },
    ]
    model_messages.extend(
        {"role": msg.role if msg.role in {"system", "assistant", "user"} else "user", "content": msg.content}
        for msg in recent_messages
    )
    return model_messages


def _prepare_chat_context(
    *,
    db: Session,
    session: models.ChatSession,
    user_id: int,
    payload: schemas.ChatMessageCreate,
) -> tuple[list[models.UserMemory], list[models.ChatMessage], str]:
    memories = (
        db.query(models.UserMemory)
        .filter(models.UserMemory.user_id == user_id)
        .order_by(models.UserMemory.relevance.desc(), models.UserMemory.updated_at.desc())
        .limit(MEMORY_FETCH_LIMIT)
        .all()
    )

    recent_messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session.id, models.ChatMessage.user_id == user_id)
        .order_by(models.ChatMessage.created_at.desc(), models.ChatMessage.id.desc())
        .limit(RECENT_CHAT_LIMIT)
        .all()
    )
    recent_messages = list(reversed(recent_messages))

    live_context_chunks: list[str] = []
    for action in _build_prefetch_actions(payload):
        tool_name = action.path.replace("/ai/tools/", "", 1).strip("/")
        if tool_name not in READ_ONLY_TOOLS:
            continue
        result = run_tool(tool_name, _sanitize_tool_args(tool_name, action.body or {}))
        if result.success:
            live_context_chunks.append(f"{tool_name}: {_compact_json(result.data)}")
        else:
            live_context_chunks.append(f"{tool_name}: ERROR {_compact_json(result.data)}")

    return memories, recent_messages, ("\n".join(live_context_chunks) if live_context_chunks else "(none)")


def _autonomous_execute(
    *,
    db: Session,
    current_user: models.User,
    actions: list[schemas.AIProposedAction],
) -> tuple[list[str], list[schemas.AIProposedAction], bool]:
    execution_lines: list[str] = []
    failed = False
    for action in actions:
        tool_name = action.path.replace("/ai/tools/", "", 1).strip("/")
        ok, result_data = _execute_tool_action(
            tool_name=tool_name,
            tool_args=action.body or {},
            current_user=current_user,
            db=db,
        )
        if ok:
            execution_lines.append(f"✅ {action.label}: {_compact_json(result_data, max_len=400)}")
        else:
            failed = True
            execution_lines.append(f"❌ {action.label}: {_compact_json(result_data, max_len=400)}")
    return execution_lines, [], failed


def _run_chat_rounds(
    *,
    db: Session,
    session: models.ChatSession,
    payload: schemas.ChatMessageCreate,
    current_user: models.User,
    autonomous_mode: bool,
    max_rounds: int,
) -> tuple[str, list[schemas.AIProposedAction], bool, int]:
    working_payload = schemas.ChatMessageCreate(message=payload.message, context=payload.context)
    final_reply = ""
    last_actions: list[schemas.AIProposedAction] = []
    done = False

    for round_idx in range(1, max_rounds + 1):
        memories, recent_messages, live_context_block = _prepare_chat_context(
            db=db,
            session=session,
            user_id=current_user.id,
            payload=working_payload,
        )
        model_messages = _build_model_messages(
            payload=working_payload,
            memories=memories,
            recent_messages=recent_messages,
            live_context_block=live_context_block,
        )

        raw_reply = _chat(model_messages, temperature=0.2).strip()
        reply, proposed_actions, model_done = _parse_ai_assistant_output(raw_reply)

        if not proposed_actions:
            proposed_actions = _build_bootstrap_actions(working_payload)

        final_reply = reply
        last_actions = proposed_actions
        done = model_done

        if autonomous_mode and proposed_actions:
            lines, _, failed = _autonomous_execute(db=db, current_user=current_user, actions=proposed_actions)
            final_reply = (final_reply + "\n\nAutonomous execution:\n" + "\n".join(lines)).strip()
            last_actions = []
            if failed:
                done = True
            if done:
                return final_reply, last_actions, done, round_idx

            working_payload = schemas.ChatMessageCreate(
                message=(
                    "Continue from previous step. Use tool results already captured in context. "
                    "Return JSON with done=true when objective is complete."
                ),
                context={
                    **(payload.context or {}),
                    "background_round": round_idx,
                },
            )
            continue

        return final_reply, last_actions, done, round_idx

    return final_reply, last_actions, False, max_rounds


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
    session = _get_user_session_or_404(db, session_id=session_id, user_id=current_user.id)
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session.id, models.ChatMessage.user_id == current_user.id)
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

    request_autonomous_mode = True
    if isinstance(payload.context, dict) and "autonomous_mode" in payload.context:
        request_autonomous_mode = bool(payload.context.get("autonomous_mode"))

    reply, proposed_actions, _done, _rounds = _run_chat_rounds(
        db=db,
        session=session,
        payload=payload,
        current_user=current_user,
        autonomous_mode=request_autonomous_mode,
        max_rounds=1,
    )

    assistant_msg = models.ChatMessage(session_id=session.id, user_id=current_user.id, role="assistant", content=reply)
    db.add(assistant_msg)
    session.updated_at = datetime.utcnow()

    recent_messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session.id, models.ChatMessage.user_id == current_user.id)
        .order_by(models.ChatMessage.created_at.desc(), models.ChatMessage.id.desc())
        .limit(RECENT_CHAT_LIMIT)
        .all()
    )
    recent_messages = list(reversed(recent_messages))

    memory_updated = _extract_memories(
        db,
        user_id=current_user.id,
        snippet_messages=recent_messages[-MEMORY_TURNS_FOR_EXTRACTION:],
        assistant_reply=reply,
    )
    db.commit()
    return schemas.ChatReplyOut(reply=reply, memory_updated=memory_updated, proposed_actions=proposed_actions)


@router.post("/sessions/{session_id}/background-run", response_model=schemas.ChatBackgroundRunOut)
def background_run(
    session_id: int,
    payload: schemas.ChatBackgroundRunRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = _get_user_session_or_404(db, session_id=session_id, user_id=current_user.id)
    goal = (payload.goal or "").strip()
    if not goal:
        raise HTTPException(status_code=400, detail="Goal cannot be empty")

    user_msg = models.ChatMessage(session_id=session.id, user_id=current_user.id, role="user", content=goal)
    db.add(user_msg)
    db.flush()

    max_rounds = max(1, min(int(payload.max_rounds or 6), BACKGROUND_MAX_ROUNDS))
    reply, last_actions, done, rounds = _run_chat_rounds(
        db=db,
        session=session,
        payload=schemas.ChatMessageCreate(message=goal, context={**(payload.context or {}), "background_mode": True}),
        current_user=current_user,
        autonomous_mode=True,
        max_rounds=max_rounds,
    )

    assistant_msg = models.ChatMessage(session_id=session.id, user_id=current_user.id, role="assistant", content=reply)
    db.add(assistant_msg)
    session.updated_at = datetime.utcnow()
    db.commit()
    return schemas.ChatBackgroundRunOut(reply=reply, rounds_executed=rounds, done=done, last_actions=last_actions)


def _sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/sessions/{session_id}/messages/stream")
def stream_message(
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
    db.commit()

    memories, recent_messages, live_context_block = _prepare_chat_context(
        db=db,
        session=session,
        user_id=current_user.id,
        payload=payload,
    )
    model_messages = _build_model_messages(
        payload=payload,
        memories=memories,
        recent_messages=recent_messages,
        live_context_block=live_context_block,
    )

    q: queue.Queue[tuple[str, Any]] = queue.Queue()
    final_raw = {"value": ""}

    def _worker() -> None:
        try:
            for token in _chat_stream(model_messages, temperature=0.2):
                final_raw["value"] += token
                q.put(("token", token))
            q.put(("done", None))
        except Exception as exc:  # noqa: BLE001
            q.put(("error", str(exc)))

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

    def _event_iter() -> Iterator[str]:
        accumulated = ""
        while True:
            try:
                kind, payload_item = q.get(timeout=0.2)
            except queue.Empty:
                yield ": keep-alive\n\n"
                continue

            if kind == "token":
                accumulated += str(payload_item)
                yield _sse_event("token", {"delta": payload_item})
                continue

            if kind == "error":
                yield _sse_event("error", {"message": str(payload_item)})
                break

            if kind == "done":
                reply, proposed_actions, _done = _parse_ai_assistant_output(accumulated)
                if not proposed_actions:
                    proposed_actions = _build_bootstrap_actions(payload)

                request_autonomous_mode = True
                if isinstance(payload.context, dict) and "autonomous_mode" in payload.context:
                    request_autonomous_mode = bool(payload.context.get("autonomous_mode"))

                if request_autonomous_mode and proposed_actions:
                    lines, _, _failed = _autonomous_execute(db=db, current_user=current_user, actions=proposed_actions)
                    if lines:
                        reply = (reply + "\n\nAutonomous execution:\n" + "\n".join(lines)).strip()
                    proposed_actions = []

                assistant_msg = models.ChatMessage(
                    session_id=session.id,
                    user_id=current_user.id,
                    role="assistant",
                    content=reply,
                )
                db.add(assistant_msg)
                session.updated_at = datetime.utcnow()

                recent_after = (
                    db.query(models.ChatMessage)
                    .filter(models.ChatMessage.session_id == session.id, models.ChatMessage.user_id == current_user.id)
                    .order_by(models.ChatMessage.created_at.desc(), models.ChatMessage.id.desc())
                    .limit(RECENT_CHAT_LIMIT)
                    .all()
                )
                recent_after = list(reversed(recent_after))
                memory_updated = _extract_memories(
                    db,
                    user_id=current_user.id,
                    snippet_messages=recent_after[-MEMORY_TURNS_FOR_EXTRACTION:],
                    assistant_reply=reply,
                )
                db.commit()

                yield _sse_event(
                    "final",
                    {
                        "reply": reply,
                        "memory_updated": memory_updated,
                        "proposed_actions": [a.model_dump() for a in proposed_actions],
                    },
                )
                break

        yield _sse_event("close", {"ok": True})

    return StreamingResponse(_event_iter(), media_type="text/event-stream")


@router.post("/execute", response_model=schemas.AIExecuteResponse)
def execute_action(
    payload: schemas.AIExecuteRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Execution requires explicit confirmation")
    if payload.method != "POST":
        raise HTTPException(status_code=400, detail="Only POST actions are supported")
    if not payload.path.startswith("/ai/tools/"):
        raise HTTPException(status_code=400, detail="Unsupported action path")

    tool_name = payload.path.replace("/ai/tools/", "", 1).strip("/")
    ok, result_data = _execute_tool_action(
        tool_name=tool_name,
        tool_args=payload.body or {},
        current_user=current_user,
        db=db,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=result_data)
    return schemas.AIExecuteResponse(ok=True, result=result_data)


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
