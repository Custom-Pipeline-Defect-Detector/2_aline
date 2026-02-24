from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.rbac import PROJECTS_READ_ROLES, PROJECTS_WRITE_ROLES
from app.deps import get_db, get_current_user, require_roles

router = APIRouter(prefix="", tags=["bom-items"])



def _log_audit(db: Session, actor_id: int, action: str, entity_id: int, before, after):
    db.add(
        models.AuditLog(
            actor_user_id=actor_id,
            action=action,
            entity_table="bom_items",
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
    "/projects/{project_id}/bom-items",
    response_model=list[schemas.BOMItemOut],
    dependencies=[Depends(require_roles(PROJECTS_READ_ROLES))],
)
def list_bom_items(project_id: int, db: Session = Depends(get_db)):
    items = (
        db.query(models.BOMItem)
        .filter(models.BOMItem.project_id == project_id)
        .order_by(models.BOMItem.created_at.desc())
        .all()
    )
    return [
        schemas.BOMItemOut(
            id=item.id,
            project_id=item.project_id,
            part_no=item.part_no,
            name=item.name,
            qty=item.qty,
            supplier=item.supplier,
            lead_time_days=item.lead_time_days,
            status=item.status,
            created_at=item.created_at,
            project_name=item.project.name if item.project else None,
            project_code=item.project.project_code if item.project else None,
        )
        for item in items
    ]


@router.post(
    "/projects/{project_id}/bom-items",
    response_model=schemas.BOMItemOut,
    dependencies=[Depends(require_roles(PROJECTS_WRITE_ROLES))],
)
def create_bom_item(
    project_id: int,
    payload: schemas.BOMItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = _resolve_project(db, project_id, payload.project_code)
    item = models.BOMItem(
        project_id=project.id,
        part_no=payload.part_no,
        name=payload.name,
        qty=payload.qty,
        supplier=payload.supplier,
        lead_time_days=payload.lead_time_days,
        status=payload.status or "pending",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    _log_audit(db, current_user.id, "created", item.id, None, {"part_no": item.part_no})
    db.commit()
    return schemas.BOMItemOut(
        id=item.id,
        project_id=item.project_id,
        part_no=item.part_no,
        name=item.name,
        qty=item.qty,
        supplier=item.supplier,
        lead_time_days=item.lead_time_days,
        status=item.status,
        created_at=item.created_at,
        project_name=project.name,
        project_code=project.project_code,
    )


@router.patch(
    "/bom-items/{item_id}",
    response_model=schemas.BOMItemOut,
    dependencies=[Depends(require_roles(PROJECTS_WRITE_ROLES))],
)
def update_bom_item(
    item_id: int,
    payload: schemas.BOMItemUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    item = db.query(models.BOMItem).filter_by(id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="BOM item not found")
    before = {"part_no": item.part_no, "status": item.status}
    updates = payload.model_dump(exclude_unset=True)
    if "project_id" in updates or "project_code" in updates:
        project = _resolve_project(db, updates.get("project_id"), updates.get("project_code"))
        item.project_id = project.id
        updates.pop("project_id", None)
        updates.pop("project_code", None)
    for field, value in updates.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    _log_audit(db, current_user.id, "updated", item.id, before, {"part_no": item.part_no, "status": item.status})
    db.commit()
    return schemas.BOMItemOut(
        id=item.id,
        project_id=item.project_id,
        part_no=item.part_no,
        name=item.name,
        qty=item.qty,
        supplier=item.supplier,
        lead_time_days=item.lead_time_days,
        status=item.status,
        created_at=item.created_at,
        project_name=item.project.name if item.project else None,
        project_code=item.project.project_code if item.project else None,
    )


@router.delete(
    "/bom-items/{item_id}",
    status_code=204,
    dependencies=[Depends(require_roles(PROJECTS_WRITE_ROLES))],
)
def delete_bom_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    item = db.query(models.BOMItem).filter_by(id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="BOM item not found")
    before = {"part_no": item.part_no, "status": item.status}
    db.delete(item)
    db.commit()
    _log_audit(db, current_user.id, "deleted", item_id, before, None)
    db.commit()
    return None
