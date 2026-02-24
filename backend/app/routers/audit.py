from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.rbac import AUDIT_READ_ROLES
from app.deps import get_db, require_roles

router = APIRouter(prefix="/audit", tags=["audit"])



@router.get("", response_model=list[schemas.AuditLogOut], dependencies=[Depends(require_roles(AUDIT_READ_ROLES))])
def list_audit_logs(
    db: Session = Depends(get_db),
    entity_type: str | None = None,
    entity_id: int | None = None,
):
    query = db.query(models.AuditLog)
    if entity_type:
        query = query.filter(models.AuditLog.entity_table == entity_type)
    if entity_id:
        query = query.filter(models.AuditLog.entity_id == entity_id)
    logs = query.order_by(models.AuditLog.created_at.desc()).limit(200).all()
    return logs
