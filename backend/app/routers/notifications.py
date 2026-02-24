from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app import models, schemas
from app.rbac import NOTIFICATION_READ_ROLES, NOTIFICATION_WRITE_ROLES
from app.deps import get_db, get_current_user, require_roles


router = APIRouter(prefix="/notifications", tags=["notifications"])



@router.get("", response_model=list[schemas.NotificationOut], dependencies=[Depends(require_roles(NOTIFICATION_READ_ROLES))])
def list_notifications(unread_only: bool = False, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    roles = [role.name for role in user.roles]
    query = db.query(models.Notification).filter(
        or_(
            models.Notification.user_id == user.id,
            models.Notification.role.in_(roles),
        )
    )
    if unread_only:
        query = query.filter(models.Notification.is_read.is_(False))
    return query.order_by(models.Notification.created_at.desc()).limit(50).all()


@router.post("/{notification_id}/read", response_model=schemas.NotificationOut, dependencies=[Depends(require_roles(NOTIFICATION_WRITE_ROLES))])
def mark_read(notification_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    notification = db.query(models.Notification).filter_by(id=notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/read_all", status_code=204, dependencies=[Depends(require_roles(NOTIFICATION_WRITE_ROLES))])
def mark_all_read(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    roles = [role.name for role in user.roles]
    db.query(models.Notification).filter(
        or_(
            models.Notification.user_id == user.id,
            models.Notification.role.in_(roles),
        )
    ).update({models.Notification.is_read: True})
    db.commit()
    return None
