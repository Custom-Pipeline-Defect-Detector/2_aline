from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app import models, schemas
from app.auth import verify_password, create_access_token, get_password_hash
from app.core.config import settings
from app.deps import get_db, get_current_user

REGISTERABLE_ROLES = {"Viewer", "Sales", "Engineer", "Technician", "QC", "PM", "Manager"}

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_access_token(
        subject=user.email,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserOut)
def read_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.post("/register", response_model=schemas.UserOut)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(
        email=payload.email,
        name=payload.name,
        password_hash=get_password_hash(payload.password),
        is_active=True,
    )

    requested_role_name = payload.role_name or "Viewer"
    if requested_role_name not in REGISTERABLE_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role selected")

    selected_role = db.query(models.Role).filter(models.Role.name == requested_role_name).first()
    if not selected_role:
        selected_role = db.query(models.Role).filter(models.Role.name == "Viewer").first()
    if selected_role:
        user.roles = [selected_role]
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
