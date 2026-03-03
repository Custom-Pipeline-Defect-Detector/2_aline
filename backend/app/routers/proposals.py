from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.config import settings
from app.deps import get_db, require_roles, get_current_user
from app.rbac import PROPOSALS_APPROVE_ROLES, PROPOSALS_READ_ROLES
from app.services.customers import find_similar_customer

router = APIRouter(prefix="/proposals", tags=["proposals"])


def _log_audit(
    db: Session,
    actor_id: int,
    action: str,
    entity_table: str,
    entity_id: int,
    before,
    after,
):
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


def _resolve_project(db: Session, proposed_fields: dict) -> models.Project:
    project_code = proposed_fields.get("project_code")
    if project_code:
        project = db.query(models.Project).filter_by(project_code=project_code).first()
        if project:
            return project

    project = db.query(models.Project).first()
    if not project:
        customer = db.query(models.Customer).first()
        if not customer:
            customer = models.Customer(name="Default Customer", aliases=[])
            db.add(customer)
            db.flush()
        project = models.Project(
            project_code="AUTO-001",
            name="Auto Project",
            customer_id=customer.id,
        )
        db.add(project)
        db.flush()
    return project


def _normalize_aliases(raw_aliases) -> list[str]:
    if not isinstance(raw_aliases, list):
        return []
    aliases: list[str] = []
    for alias in raw_aliases:
        text = str(alias or "").strip()
        if text:
            aliases.append(text)
    return sorted(set(aliases))


def _upsert_customer_from_fields(db: Session, proposal: models.Proposal) -> models.Customer:
    proposed_fields = proposal.proposed_fields or {}
    name = str(proposed_fields.get("name") or "").strip() or f"Auto Customer {proposal.id}"
    aliases = _normalize_aliases(proposed_fields.get("aliases"))

    customer = None
    if proposal.target_entity_id:
        customer = db.query(models.Customer).filter(models.Customer.id == proposal.target_entity_id).first()
    if not customer:
        customer = find_similar_customer(db, name) or db.query(models.Customer).filter(models.Customer.name == name).first()

    if customer:
        customer.aliases = sorted({*(customer.aliases or []), *aliases})
    else:
        customer = models.Customer(name=name, aliases=aliases)
        db.add(customer)
        db.flush()

    return customer


def _resolve_customer_for_project(db: Session, proposed_fields: dict) -> models.Customer:
    customer_id = proposed_fields.get("customer_id")
    if customer_id:
        customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
        if customer:
            return customer

    customer_name = str(proposed_fields.get("customer_name") or "").strip()
    if customer_name:
        customer = find_similar_customer(db, customer_name) or db.query(models.Customer).filter(
            models.Customer.name == customer_name
        ).first()
        if customer:
            return customer

    customer = db.query(models.Customer).first()
    if customer:
        return customer

    customer = models.Customer(name="Default Customer", aliases=[])
    db.add(customer)
    db.flush()
    return customer


def _upsert_project_from_fields(db: Session, proposal: models.Proposal) -> models.Project:
    proposed_fields = proposal.proposed_fields or {}
    project_code = str(proposed_fields.get("project_code") or "").strip()
    project_name = str(proposed_fields.get("name") or "").strip() or project_code or f"Project {proposal.id}"

    project = None
    if proposal.target_entity_id:
        project = db.query(models.Project).filter(models.Project.id == proposal.target_entity_id).first()
    if not project and project_code:
        project = db.query(models.Project).filter(models.Project.project_code == project_code).first()

    customer = _resolve_customer_for_project(db, proposed_fields)

    if project is None:
        project = (
            db.query(models.Project)
            .filter(models.Project.customer_id == customer.id, models.Project.name == project_name)
            .first()
        )

    if not project:
        project = models.Project(
            project_code=project_code or f"AUTO-{proposal.id}",
            name=project_name,
            customer_id=customer.id,
            stage=str(proposed_fields.get("stage") or "intake"),
            value_amount=proposed_fields.get("value_amount"),
            currency=str(proposed_fields.get("currency") or "CNY"),
        )
        db.add(project)
        db.flush()
    else:
        project.name = project_name
        project.customer_id = customer.id
        if project_code:
            project.project_code = project_code
        if proposed_fields.get("stage") is not None:
            project.stage = str(proposed_fields.get("stage"))
        if proposed_fields.get("status") is not None:
            project.status = str(proposed_fields.get("status"))
        if proposed_fields.get("value_amount") is not None:
            project.value_amount = proposed_fields.get("value_amount")
        if proposed_fields.get("currency") is not None:
            project.currency = str(proposed_fields.get("currency"))

    return project


@router.get(
    "",
    response_model=list[schemas.ProposalOut],
    dependencies=[
        Depends(
            require_roles(PROPOSALS_READ_ROLES)
        )
    ],
)
def list_proposals(db: Session = Depends(get_db), status: str | None = None):
    query = db.query(models.Proposal)
    if status:
        query = query.filter(models.Proposal.status == status)
    return query.order_by(models.Proposal.created_at.desc()).all()


@router.get(
    "/{proposal_id}",
    response_model=schemas.ProposalOut,
    dependencies=[Depends(require_roles(PROPOSALS_READ_ROLES))],
)
def get_proposal(proposal_id: int, db: Session = Depends(get_db)):
    proposal = db.query(models.Proposal).filter_by(id=proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


@router.put(
    "/{proposal_id}",
    response_model=schemas.ProposalOut,
    dependencies=[Depends(require_roles(PROPOSALS_APPROVE_ROLES))],
)
def update_proposal(proposal_id: int, payload: schemas.ProposalUpdate, db: Session = Depends(get_db)):
    proposal = db.query(models.Proposal).filter_by(id=proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    proposal.proposed_fields = payload.proposed_fields
    proposal.field_confidence = payload.field_confidence
    proposal.evidence = payload.evidence
    proposal.questions = payload.questions

    db.commit()
    db.refresh(proposal)
    return proposal


def _apply_decision(
    proposal: models.Proposal,
    payload: schemas.ProposalDecision,
    db: Session,
    current_user: models.User,
):
    """
    Internal helper (NOT a route).
    Applies approve/reject decision and, if approved, writes to target tables + audit log.
    """
    if payload.status not in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail="Invalid status")

    proposal.status = payload.status
    proposal.reviewed_at = datetime.utcnow()
    proposal.reviewer_id = current_user.id

    # Rejected: record reason in questions and stop.
    if payload.status == "rejected":
        questions = proposal.questions or {}
        questions["rejected_reason"] = payload.reviewer_note or ""
        proposal.questions = questions
        _log_audit(
            db,
            current_user.id,
            "rejected",
            "proposals",
            proposal.id,
            {"status": "pending"},
            {"status": "rejected"},
        )
        db.commit()
        db.refresh(proposal)
        return proposal

    # Approved - apply to core tables
    before = None
    after = None

    if proposal.target_table == "customers":
        customer = _upsert_customer_from_fields(db, proposal)
        after = {"id": customer.id, "name": customer.name}
        _log_audit(
            db,
            current_user.id,
            "upsert",
            "customers",
            customer.id,
            before,
            after,
        )

    elif proposal.target_table == "projects":
        project = _upsert_project_from_fields(db, proposal)
        after = {"id": project.id, "project_code": project.project_code}
        _log_audit(db, current_user.id, "upsert", "projects", project.id, before, after)

    elif proposal.target_table == "tasks":
        task = None
        if proposal.target_entity_id:
            task = db.query(models.Task).filter(models.Task.id == proposal.target_entity_id).first()
        if not task:
            project = _resolve_project(db, proposal.proposed_fields)
            task = models.Task(
                project_id=project.id,
                title=proposal.proposed_fields.get("title") or "Task",
                description=proposal.proposed_fields.get("description"),
                status=proposal.proposed_fields.get("status") or "open",
            )
            db.add(task)
            db.flush()
        else:
            if proposal.proposed_fields.get("title") is not None:
                task.title = proposal.proposed_fields.get("title")
            if proposal.proposed_fields.get("description") is not None:
                task.description = proposal.proposed_fields.get("description")
            if proposal.proposed_fields.get("status") is not None:
                task.status = proposal.proposed_fields.get("status")
        after = {"id": task.id, "title": task.title}
        _log_audit(db, current_user.id, "upsert", "tasks", task.id, before, after)

    elif proposal.target_table == "issues":
        issue = None
        if proposal.target_entity_id:
            issue = db.query(models.Issue).filter(models.Issue.id == proposal.target_entity_id).first()
        if not issue:
            project = _resolve_project(db, proposal.proposed_fields)
            issue = models.Issue(
                project_id=project.id,
                severity=proposal.proposed_fields.get("severity") or "medium",
                description=proposal.proposed_fields.get("description") or "Issue",
                status=proposal.proposed_fields.get("status") or "open",
            )
            db.add(issue)
            db.flush()
        else:
            if proposal.proposed_fields.get("severity") is not None:
                issue.severity = proposal.proposed_fields.get("severity")
            if proposal.proposed_fields.get("description") is not None:
                issue.description = proposal.proposed_fields.get("description")
            if proposal.proposed_fields.get("status") is not None:
                issue.status = proposal.proposed_fields.get("status")
        after = {"id": issue.id, "severity": issue.severity}
        _log_audit(db, current_user.id, "upsert", "issues", issue.id, before, after)

    elif proposal.target_table == "ncrs":
        ncr = None
        if proposal.target_entity_id:
            ncr = db.query(models.NCR).filter(models.NCR.id == proposal.target_entity_id).first()
        if not ncr:
            project = _resolve_project(db, proposal.proposed_fields)
            ncr = models.NCR(
                project_id=project.id,
                description=proposal.proposed_fields.get("description") or "NCR",
                root_cause=proposal.proposed_fields.get("root_cause"),
                corrective_action=proposal.proposed_fields.get("corrective_action"),
                status=proposal.proposed_fields.get("status") or "open",
            )
            db.add(ncr)
            db.flush()
        else:
            if proposal.proposed_fields.get("description") is not None:
                ncr.description = proposal.proposed_fields.get("description")
            if proposal.proposed_fields.get("root_cause") is not None:
                ncr.root_cause = proposal.proposed_fields.get("root_cause")
            if proposal.proposed_fields.get("corrective_action") is not None:
                ncr.corrective_action = proposal.proposed_fields.get("corrective_action")
            if proposal.proposed_fields.get("status") is not None:
                ncr.status = proposal.proposed_fields.get("status")
        after = {"id": ncr.id, "description": ncr.description}
        _log_audit(db, current_user.id, "upsert", "ncrs", ncr.id, before, after)

    else:
        raise HTTPException(status_code=400, detail="Unsupported target table")

    db.commit()
    db.refresh(proposal)
    _log_audit(
        db,
        current_user.id,
        "approved",
        "proposals",
        proposal.id,
        {"status": "pending"},
        {"status": "approved"},
    )
    db.commit()
    return proposal


def _auto_approve_if_enabled(
    proposal: models.Proposal,
    db: Session,
    current_user: models.User,
) -> models.Proposal:
    if not settings.auto_approve_proposals:
        return proposal
    if proposal.status != "pending":
        return proposal
    return _apply_decision(proposal, schemas.ProposalDecision(status="approved"), db, current_user)


@router.post(
    "/{proposal_id}/decision",
    response_model=schemas.ProposalOut,
    dependencies=[Depends(require_roles(PROPOSALS_APPROVE_ROLES))],
)
def decide_proposal(
    proposal_id: int,
    payload: schemas.ProposalDecision,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    proposal = db.query(models.Proposal).filter_by(id=proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return _apply_decision(proposal, payload, db, current_user)


@router.post(
    "/{proposal_id}/approve",
    response_model=schemas.ProposalOut,
    dependencies=[Depends(require_roles(PROPOSALS_APPROVE_ROLES))],
)
def approve_proposal(
    proposal_id: int,
    payload: schemas.ProposalApprove,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    proposal = db.query(models.Proposal).filter_by(id=proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    proposal.proposed_fields = payload.proposed_fields
    decision = schemas.ProposalDecision(status="approved")
    return _apply_decision(proposal, decision, db, current_user)


@router.post(
    "/auto-approve-pending",
    dependencies=[Depends(require_roles(PROPOSALS_APPROVE_ROLES))],
)
def auto_approve_pending(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    pending = (
        db.query(models.Proposal)
        .filter(models.Proposal.status == "pending")
        .order_by(models.Proposal.created_at.asc())
        .limit(max(1, min(limit, 500)))
        .all()
    )

    approved_ids: list[int] = []
    failed: list[dict[str, str]] = []
    for proposal in pending:
        try:
            _apply_decision(
                proposal,
                schemas.ProposalDecision(status="approved"),
                db,
                current_user,
            )
            approved_ids.append(proposal.id)
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            failed.append({"proposal_id": str(proposal.id), "error": str(exc)})

    return {
        "approved_count": len(approved_ids),
        "approved_ids": approved_ids,
        "failed": failed,
    }


@router.post(
    "/{proposal_id}/reject",
    response_model=schemas.ProposalOut,
    dependencies=[Depends(require_roles(PROPOSALS_APPROVE_ROLES))],
)
def reject_proposal(
    proposal_id: int,
    payload: schemas.ProposalReject,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    proposal = db.query(models.Proposal).filter_by(id=proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    decision = schemas.ProposalDecision(status="rejected", reviewer_note=payload.reason)
    return _apply_decision(proposal, decision, db, current_user)
