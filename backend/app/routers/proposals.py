from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import get_db, require_roles, get_current_user
from app.rbac import PROPOSALS_APPROVE_ROLES, PROPOSALS_READ_ROLES

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
        customer = models.Customer(
            name=proposal.proposed_fields.get("name"),
            aliases=proposal.proposed_fields.get("aliases", []),
        )
        db.add(customer)
        db.flush()
        after = {"id": customer.id, "name": customer.name}
        _log_audit(db, current_user.id, "create", "customers", customer.id, before, after)

    elif proposal.target_table == "projects":
        customer = db.query(models.Customer).first()
        if not customer:
            customer = models.Customer(name="Default Customer", aliases=[])
            db.add(customer)
            db.flush()

        project = models.Project(
            project_code=proposal.proposed_fields.get("project_code") or f"AUTO-{proposal.id}",
            name=proposal.proposed_fields.get("name") or "New Project",
            customer_id=customer.id,
            stage=proposal.proposed_fields.get("stage") or "intake",
            value_amount=proposal.proposed_fields.get("value_amount"),
            currency=proposal.proposed_fields.get("currency") or "CNY",
        )
        db.add(project)
        db.flush()
        after = {"id": project.id, "project_code": project.project_code}
        _log_audit(db, current_user.id, "create", "projects", project.id, before, after)

    elif proposal.target_table == "tasks":
        project = _resolve_project(db, proposal.proposed_fields)
        task = models.Task(
            project_id=project.id,
            title=proposal.proposed_fields.get("title") or "Task",
            description=proposal.proposed_fields.get("description"),
            status="open",
        )
        db.add(task)
        db.flush()
        after = {"id": task.id, "title": task.title}
        _log_audit(db, current_user.id, "create", "tasks", task.id, before, after)

    elif proposal.target_table == "issues":
        project = _resolve_project(db, proposal.proposed_fields)
        issue = models.Issue(
            project_id=project.id,
            severity=proposal.proposed_fields.get("severity") or "medium",
            description=proposal.proposed_fields.get("description") or "Issue",
            status="open",
        )
        db.add(issue)
        db.flush()
        after = {"id": issue.id, "severity": issue.severity}
        _log_audit(db, current_user.id, "create", "issues", issue.id, before, after)

    elif proposal.target_table == "ncrs":
        project = _resolve_project(db, proposal.proposed_fields)
        ncr = models.NCR(
            project_id=project.id,
            description=proposal.proposed_fields.get("description") or "NCR",
            root_cause=proposal.proposed_fields.get("root_cause"),
            corrective_action=proposal.proposed_fields.get("corrective_action"),
            status="open",
        )
        db.add(ncr)
        db.flush()
        after = {"id": ncr.id, "description": ncr.description}
        _log_audit(db, current_user.id, "create", "ncrs", ncr.id, before, after)

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
