from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.rbac import QUALITY_READ_ROLES, QUALITY_WRITE_ROLES
from app.deps import get_db, get_current_user, require_roles

router = APIRouter(prefix="", tags=["inspection"])



def _log_audit(db: Session, actor_id: int, action: str, entity_table: str, entity_id: int, before, after):
    db.add(
        models.AuditLog(
            actor_user_id=actor_id,
            action=action,
            entity_table=entity_table,
            entity_id=entity_id,
            before=before,
            after=after,
        )
    )


def _resolve_project(db: Session, project_id: int | None, project_code: str | None):
    if project_id:
        project = db.query(models.Project).filter_by(id=project_id).first()
        if project:
            return project
    if project_code:
        project = db.query(models.Project).filter_by(project_code=project_code).first()
        if project:
            return project
    raise HTTPException(status_code=400, detail="Project not found")


@router.get(
    "/inspection-records",
    response_model=list[schemas.InspectionRecordOut],
    dependencies=[Depends(require_roles(QUALITY_READ_ROLES))],
)
def list_inspections(db: Session = Depends(get_db), project_id: int | None = None):
    query = db.query(models.InspectionRecord)
    if project_id:
        query = query.filter(models.InspectionRecord.project_id == project_id)
    records = query.order_by(models.InspectionRecord.date.desc()).all()
    return [
        schemas.InspectionRecordOut(
            id=record.id,
            project_id=record.project_id,
            inspector_id=record.inspector_id,
            date=record.date,
            status=record.status,
            summary=record.summary,
            created_at=record.created_at,
            project_name=record.project.name if record.project else None,
            project_code=record.project.project_code if record.project else None,
        )
        for record in records
    ]


@router.post(
    "/inspection-records",
    response_model=schemas.InspectionRecordOut,
    dependencies=[Depends(require_roles(QUALITY_WRITE_ROLES))],
)
def create_inspection(
    payload: schemas.InspectionRecordCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = _resolve_project(db, payload.project_id, payload.project_code)
    record = models.InspectionRecord(
        project_id=project.id,
        inspector_id=payload.inspector_id or current_user.id,
        date=payload.date,
        status=payload.status or "open",
        summary=payload.summary,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    _log_audit(db, current_user.id, "created", "inspection_records", record.id, None, {"status": record.status})
    db.commit()
    return schemas.InspectionRecordOut(
        id=record.id,
        project_id=record.project_id,
        inspector_id=record.inspector_id,
        date=record.date,
        status=record.status,
        summary=record.summary,
        created_at=record.created_at,
        project_name=project.name,
        project_code=project.project_code,
    )


@router.patch(
    "/inspection-records/{record_id}",
    response_model=schemas.InspectionRecordOut,
    dependencies=[Depends(require_roles(QUALITY_WRITE_ROLES))],
)
def update_inspection(
    record_id: int,
    payload: schemas.InspectionRecordUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    record = db.query(models.InspectionRecord).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Inspection record not found")
    before = {"status": record.status, "summary": record.summary}
    updates = payload.model_dump(exclude_unset=True)
    if "project_id" in updates or "project_code" in updates:
        project = _resolve_project(db, updates.get("project_id"), updates.get("project_code"))
        record.project_id = project.id
        updates.pop("project_id", None)
        updates.pop("project_code", None)
    for field, value in updates.items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    _log_audit(db, current_user.id, "updated", "inspection_records", record.id, before, {"status": record.status})
    db.commit()
    return schemas.InspectionRecordOut(
        id=record.id,
        project_id=record.project_id,
        inspector_id=record.inspector_id,
        date=record.date,
        status=record.status,
        summary=record.summary,
        created_at=record.created_at,
        project_name=record.project.name if record.project else None,
        project_code=record.project.project_code if record.project else None,
    )


@router.delete(
    "/inspection-records/{record_id}",
    status_code=204,
    dependencies=[Depends(require_roles(QUALITY_WRITE_ROLES))],
)
def delete_inspection(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    record = db.query(models.InspectionRecord).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Inspection record not found")
    before = {"status": record.status, "summary": record.summary}
    db.delete(record)
    db.commit()
    _log_audit(db, current_user.id, "deleted", "inspection_records", record_id, before, None)
    db.commit()
    return None


@router.get(
    "/inspection-records/{record_id}/items",
    response_model=list[schemas.InspectionItemOut],
    dependencies=[Depends(require_roles(QUALITY_READ_ROLES))],
)
def list_inspection_items(record_id: int, db: Session = Depends(get_db)):
    items = (
        db.query(models.InspectionItem)
        .filter(models.InspectionItem.inspection_id == record_id)
        .order_by(models.InspectionItem.created_at.desc())
        .all()
    )
    return [
        schemas.InspectionItemOut(
            id=item.id,
            inspection_id=item.inspection_id,
            label=item.label,
            status=item.status,
            notes=item.notes,
            created_at=item.created_at,
        )
        for item in items
    ]


@router.post(
    "/inspection-records/{record_id}/items",
    response_model=schemas.InspectionItemOut,
    dependencies=[Depends(require_roles(QUALITY_WRITE_ROLES))],
)
def create_inspection_item(
    record_id: int,
    payload: schemas.InspectionItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    record = db.query(models.InspectionRecord).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Inspection record not found")
    item = models.InspectionItem(
        inspection_id=record_id,
        label=payload.label,
        status=payload.status or "pending",
        notes=payload.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    _log_audit(db, current_user.id, "created", "inspection_items", item.id, None, {"label": item.label})
    db.commit()
    return schemas.InspectionItemOut(
        id=item.id,
        inspection_id=item.inspection_id,
        label=item.label,
        status=item.status,
        notes=item.notes,
        created_at=item.created_at,
    )


@router.patch(
    "/inspection-items/{item_id}",
    response_model=schemas.InspectionItemOut,
    dependencies=[Depends(require_roles(QUALITY_WRITE_ROLES))],
)
def update_inspection_item(
    item_id: int,
    payload: schemas.InspectionItemUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    item = db.query(models.InspectionItem).filter_by(id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inspection item not found")
    before = {"label": item.label, "status": item.status}
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    _log_audit(db, current_user.id, "updated", "inspection_items", item.id, before, {"label": item.label, "status": item.status})
    db.commit()
    return schemas.InspectionItemOut(
        id=item.id,
        inspection_id=item.inspection_id,
        label=item.label,
        status=item.status,
        notes=item.notes,
        created_at=item.created_at,
    )


@router.delete(
    "/inspection-items/{item_id}",
    status_code=204,
    dependencies=[Depends(require_roles(QUALITY_WRITE_ROLES))],
)
def delete_inspection_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    item = db.query(models.InspectionItem).filter_by(id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inspection item not found")
    before = {"label": item.label, "status": item.status}
    db.delete(item)
    db.commit()
    _log_audit(db, current_user.id, "deleted", "inspection_items", item_id, before, None)
    db.commit()
    return None
