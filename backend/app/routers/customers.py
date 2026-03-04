import logging

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from app import models, schemas
from app.rbac import CUSTOMERS_READ_ROLES, CUSTOMERS_WRITE_ROLES
from app.deps import get_db, require_roles, get_current_user
from app.routers.projects import compute_project_health


router = APIRouter(prefix="/customers", tags=["customers"])

logger = logging.getLogger(__name__)


def _get_last_activity(db: Session, customer_id: int) -> datetime | None:
    doc_time = (
        db.query(func.max(models.Document.created_at))
        .filter(models.Document.customer_id == customer_id)
        .scalar()
    )
    audit_time = (
        db.query(func.max(models.AuditEvent.created_at))
        .filter(models.AuditEvent.entity_table == "customers", models.AuditEvent.entity_id == customer_id)
        .scalar()
    )
    if doc_time and audit_time:
        return max(doc_time, audit_time)
    return doc_time or audit_time


@router.get("", response_model=list[schemas.CustomerOut], dependencies=[Depends(require_roles(CUSTOMERS_READ_ROLES))])
def list_customers(status: str | None = None, q: str | None = None, db: Session = Depends(get_db)):
    try:
        query = db.query(models.Customer)
        if status:
            query = query.filter(models.Customer.status == status)
        if q:
            query = query.filter(models.Customer.name.ilike(f"%{q}%"))
        customers = query.order_by(models.Customer.created_at.desc()).all()
        results = []
        for customer in customers:
            documents_count = db.query(models.Document).filter(models.Document.customer_id == customer.id).count()
            active_projects = db.query(models.Project).filter(models.Project.customer_id == customer.id).count()
            # Ensure aliases is always a list
            aliases = customer.aliases if isinstance(customer.aliases, list) else []
            results.append(
                schemas.CustomerOut(
                    id=customer.id,
                    name=customer.name,
                    aliases=aliases,
                    status=customer.status,
                    industry=customer.industry,
                    owner_id=customer.owner_id,
                    notes=customer.notes,
                    tags=customer.tags,
                    created_at=customer.created_at,
                    updated_at=customer.updated_at,
                    contacts=[schemas.CustomerContactOut.model_validate(contact) for contact in customer.contacts],
                    active_projects=active_projects,
                    proposals_count=0,
                    documents_count=documents_count,
                    last_activity_at=_get_last_activity(db, customer.id),
                )
            )
        return results
    except SQLAlchemyError as exc:
        logger.exception("Customer listing unavailable due to database error")
        raise HTTPException(status_code=503, detail="Database unavailable. Run migrations and verify DB settings.") from exc


@router.post("", response_model=schemas.CustomerOut, dependencies=[Depends(require_roles(CUSTOMERS_WRITE_ROLES))])
def create_customer(
    payload: schemas.CustomerCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    normalized_name = (payload.name or "").strip()
    if not normalized_name:
        raise HTTPException(status_code=400, detail="Customer name is required")

    existing = (
        db.query(models.Customer)
        .filter(func.lower(models.Customer.name) == normalized_name.lower())
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Customer with this name already exists")

    customer = models.Customer(
        name=normalized_name,
        aliases=payload.aliases or [],
        status=payload.status or "lead",
        industry=payload.industry,
        owner_id=payload.owner_id,
        notes=payload.notes,
        tags=payload.tags or [],
    )
    db.add(customer)
    db.flush()
    if payload.contacts:
        existing_contacts = {(c.name or "", c.email or "") for c in customer.contacts}
        for contact in payload.contacts:
            key = (contact.name or "", contact.email or "")
            if key in existing_contacts:
                continue
            db.add(
                models.CustomerContact(
                    customer_id=customer.id,
                    name=contact.name,
                    email=contact.email,
                    role_title=contact.role_title,
                    phone=contact.phone,
                )
            )
    db.commit()
    db.refresh(customer)
    db.add(
        models.AuditLog(
            actor_user_id=current_user.id,
            action="created",
            entity_table="customers",
            entity_id=customer.id,
            before=None,
            after={"name": customer.name, "status": customer.status},
        )
    )
    db.commit()
    return schemas.CustomerOut(
        id=customer.id,
        name=customer.name,
        aliases=customer.aliases,
        status=customer.status,
        industry=customer.industry,
        owner_id=customer.owner_id,
        notes=customer.notes,
        tags=customer.tags,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
        contacts=[schemas.CustomerContactOut.model_validate(contact) for contact in customer.contacts],
        active_projects=0,
        proposals_count=0,
        documents_count=0,
        last_activity_at=_get_last_activity(db, customer.id),
    )


@router.get("/{customer_id}", response_model=schemas.CustomerOut, dependencies=[Depends(require_roles(CUSTOMERS_READ_ROLES))])
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(models.Customer).filter_by(id=customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    projects = []
    for project in customer.projects:
        projects.append(
            {
                "id": project.id,
                "name": project.name,
                "status": project.status,
                "health": compute_project_health(project),
            }
        )
    documents_count = db.query(models.Document).filter(models.Document.customer_id == customer.id).count()
    # Ensure aliases is always a list
    aliases = customer.aliases if isinstance(customer.aliases, list) else []
    return schemas.CustomerOut(
        id=customer.id,
        name=customer.name,
        aliases=aliases,
        status=customer.status,
        industry=customer.industry,
        owner_id=customer.owner_id,
        notes=customer.notes,
        tags=customer.tags,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
        contacts=[schemas.CustomerContactOut.model_validate(contact) for contact in customer.contacts],
        active_projects=len(customer.projects),
        proposals_count=0,
        documents_count=documents_count,
        last_activity_at=_get_last_activity(db, customer.id),
        projects=projects,
    )


@router.patch("/{customer_id}", response_model=schemas.CustomerOut, dependencies=[Depends(require_roles(CUSTOMERS_WRITE_ROLES))])
def update_customer(
    customer_id: int,
    payload: schemas.CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    customer = db.query(models.Customer).filter_by(id=customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    before = {"name": customer.name, "status": customer.status}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    db.add(
        models.AuditLog(
            actor_user_id=current_user.id,
            action="updated",
            entity_table="customers",
            entity_id=customer.id,
            before=before,
            after={"name": customer.name, "status": customer.status},
        )
    )
    db.commit()
    documents_count = db.query(models.Document).filter(models.Document.customer_id == customer.id).count()
    # Ensure aliases is always a list
    aliases = customer.aliases if isinstance(customer.aliases, list) else []
    return schemas.CustomerOut(
        id=customer.id,
        name=customer.name,
        aliases=aliases,
        status=customer.status,
        industry=customer.industry,
        owner_id=customer.owner_id,
        notes=customer.notes,
        tags=customer.tags,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
        contacts=[schemas.CustomerContactOut.model_validate(contact) for contact in customer.contacts],
        active_projects=len(customer.projects),
        proposals_count=0,
        documents_count=documents_count,
        last_activity_at=_get_last_activity(db, customer.id),
    )


@router.delete("/{customer_id}", status_code=204, dependencies=[Depends(require_roles(CUSTOMERS_WRITE_ROLES))])
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    customer = db.query(models.Customer).filter_by(id=customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    before = {"name": customer.name, "status": customer.status}
    db.delete(customer)
    db.commit()
    db.add(
        models.AuditLog(
            actor_user_id=current_user.id,
            action="deleted",
            entity_table="customers",
            entity_id=customer_id,
            before=before,
            after=None,
        )
    )
    db.commit()
    return None


@router.post("/{customer_id}/contacts", response_model=schemas.CustomerContactOut, dependencies=[Depends(require_roles(CUSTOMERS_WRITE_ROLES))])
def add_contact(customer_id: int, payload: schemas.CustomerContactCreate, db: Session = Depends(get_db)):
    customer = db.query(models.Customer).filter_by(id=customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    contact = models.CustomerContact(
        customer_id=customer_id,
        name=payload.name,
        email=payload.email,
        role_title=payload.role_title,
        phone=payload.phone,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{customer_id}/contacts/{contact_id}", status_code=204, dependencies=[Depends(require_roles(CUSTOMERS_WRITE_ROLES))])
def delete_contact(customer_id: int, contact_id: int, db: Session = Depends(get_db)):
    contact = (
        db.query(models.CustomerContact)
        .filter_by(id=contact_id, customer_id=customer_id)
        .first()
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(contact)
    db.commit()
    return None
