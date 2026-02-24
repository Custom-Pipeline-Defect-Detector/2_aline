from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.rbac import QUALITY_READ_ROLES, QUALITY_WRITE_ROLES
from app.deps import get_db, get_current_user, require_roles

router = APIRouter(prefix="/ncrs", tags=["ncrs"])



def _log_audit(db: Session, actor_id: int, action: str, entity_id: int, before, after):
    db.add(
        models.AuditLog(
            actor_user_id=actor_id,
            action=action,
            entity_table="ncrs",
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


@router.get("", response_model=list[schemas.NCROut], dependencies=[Depends(require_roles(QUALITY_READ_ROLES))])
def list_ncrs(
    db: Session = Depends(get_db),
    project_id: int | None = None,
    status: str | None = None,
):
    query = db.query(models.NCR)
    if project_id:
        query = query.filter(models.NCR.project_id == project_id)
    if status:
        query = query.filter(models.NCR.status == status)
    ncrs = query.order_by(models.NCR.created_at.desc()).all()
    results: list[schemas.NCROut] = []
    for ncr in ncrs:
        results.append(
            schemas.NCROut(
                id=ncr.id,
                project_id=ncr.project_id,
                description=ncr.description,
                root_cause=ncr.root_cause,
                corrective_action=ncr.corrective_action,
                status=ncr.status,
                source_doc_id=ncr.source_doc_id,
                opened_date=ncr.opened_date,
                closed_date=ncr.closed_date,
                created_at=ncr.created_at,
                project_name=ncr.project.name if ncr.project else None,
                project_code=ncr.project.project_code if ncr.project else None,
            )
        )
    return results


@router.get("/{ncr_id}", response_model=schemas.NCROut, dependencies=[Depends(require_roles(QUALITY_READ_ROLES))])
def get_ncr(ncr_id: int, db: Session = Depends(get_db)):
    ncr = db.query(models.NCR).filter_by(id=ncr_id).first()
    if not ncr:
        raise HTTPException(status_code=404, detail="NCR not found")
    return schemas.NCROut(
        id=ncr.id,
        project_id=ncr.project_id,
        description=ncr.description,
        root_cause=ncr.root_cause,
        corrective_action=ncr.corrective_action,
        status=ncr.status,
        source_doc_id=ncr.source_doc_id,
        opened_date=ncr.opened_date,
        closed_date=ncr.closed_date,
        created_at=ncr.created_at,
        project_name=ncr.project.name if ncr.project else None,
        project_code=ncr.project.project_code if ncr.project else None,
    )


@router.post("", response_model=schemas.NCROut, dependencies=[Depends(require_roles(QUALITY_WRITE_ROLES))])
def create_ncr(
    payload: schemas.NCRCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = _resolve_project(db, payload.project_id, payload.project_code)
    ncr = models.NCR(
        project_id=project.id,
        description=payload.description,
        root_cause=payload.root_cause,
        corrective_action=payload.corrective_action,
        status=payload.status or "open",
        source_doc_id=payload.source_doc_id,
        opened_date=payload.opened_date,
        closed_date=payload.closed_date,
    )
    db.add(ncr)
    db.commit()
    db.refresh(ncr)
    _log_audit(db, current_user.id, "created", ncr.id, None, {"description": ncr.description})
    db.commit()
    return schemas.NCROut(
        id=ncr.id,
        project_id=ncr.project_id,
        description=ncr.description,
        root_cause=ncr.root_cause,
        corrective_action=ncr.corrective_action,
        status=ncr.status,
        source_doc_id=ncr.source_doc_id,
        opened_date=ncr.opened_date,
        closed_date=ncr.closed_date,
        created_at=ncr.created_at,
        project_name=project.name,
        project_code=project.project_code,
    )


@router.patch("/{ncr_id}", response_model=schemas.NCROut, dependencies=[Depends(require_roles(QUALITY_WRITE_ROLES))])
def update_ncr(
    ncr_id: int,
    payload: schemas.NCRUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ncr = db.query(models.NCR).filter_by(id=ncr_id).first()
    if not ncr:
        raise HTTPException(status_code=404, detail="NCR not found")
    before = {"description": ncr.description, "status": ncr.status}
    updates = payload.model_dump(exclude_unset=True)
    if "project_id" in updates or "project_code" in updates:
        project = _resolve_project(db, updates.get("project_id"), updates.get("project_code"))
        ncr.project_id = project.id
        updates.pop("project_id", None)
        updates.pop("project_code", None)
    for field, value in updates.items():
        setattr(ncr, field, value)
    db.commit()
    db.refresh(ncr)
    _log_audit(db, current_user.id, "updated", ncr.id, before, {"description": ncr.description, "status": ncr.status})
    db.commit()
    return schemas.NCROut(
        id=ncr.id,
        project_id=ncr.project_id,
        description=ncr.description,
        root_cause=ncr.root_cause,
        corrective_action=ncr.corrective_action,
        status=ncr.status,
        source_doc_id=ncr.source_doc_id,
        opened_date=ncr.opened_date,
        closed_date=ncr.closed_date,
        created_at=ncr.created_at,
        project_name=ncr.project.name if ncr.project else None,
        project_code=ncr.project.project_code if ncr.project else None,
    )


@router.delete("/{ncr_id}", status_code=204, dependencies=[Depends(require_roles(QUALITY_WRITE_ROLES))])
def delete_ncr(
    ncr_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ncr = db.query(models.NCR).filter_by(id=ncr_id).first()
    if not ncr:
        raise HTTPException(status_code=404, detail="NCR not found")
    before = {"description": ncr.description, "status": ncr.status}
    db.delete(ncr)
    db.commit()
    _log_audit(db, current_user.id, "deleted", ncr_id, before, None)
    db.commit()
    return None
