from datetime import datetime

import httpx
import redis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.celery_app import celery
from app.core.config import settings
from app.deps import get_db, require_roles
from app.rbac import MANAGER_ADMIN_ROLES
from app import models

router = APIRouter(prefix="/status", tags=["status"])



def _check_db(db: Session) -> tuple[bool, str | None]:
    try:
        db.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:
        return False, str(exc)


def _check_redis() -> tuple[bool, str | None]:
    try:
        client = redis.Redis.from_url(settings.celery_broker_url)
        return bool(client.ping()), None
    except Exception as exc:
        return False, str(exc)


def _check_worker() -> tuple[bool, str | None]:
    try:
        inspector = celery.control.inspect(timeout=1)
        result = inspector.ping()
        return bool(result), None
    except Exception as exc:
        return False, str(exc)


def _check_ollama() -> tuple[bool, str | None]:
    try:
        with httpx.Client(timeout=2.0) as client:
            base_url = settings.ollama_base_url.rstrip("/")
            response = client.get(f"{base_url}/api/tags")
            ok = response.status_code < 500
            return ok, None if ok else f"HTTP {response.status_code}"
    except Exception as exc:
        return False, str(exc)


@router.get("", dependencies=[Depends(require_roles(MANAGER_ADMIN_ROLES))])
def get_status(db: Session = Depends(get_db)):
    db_ok, db_error = _check_db(db)
    redis_ok, redis_error = _check_redis()
    worker_ok, worker_error = _check_worker()
    ollama_ok, ollama_error = _check_ollama()

    last_processed = None
    if db_ok:
        last_processed = (
            db.query(models.Document.last_processed_at)
            .order_by(models.Document.last_processed_at.desc())
            .limit(1)
            .scalar()
        )

    return {
        "db_ok": db_ok,
        "redis_ok": redis_ok,
        "worker_ok": worker_ok,
        "watcher_ok": True,
        "ollama_ok": ollama_ok,
        "last_processed_doc": last_processed,
        "checked_at": datetime.utcnow(),
        "errors": {
            "db": db_error,
            "redis": redis_error,
            "worker": worker_error,
            "ollama": ollama_error,
        },
    }
