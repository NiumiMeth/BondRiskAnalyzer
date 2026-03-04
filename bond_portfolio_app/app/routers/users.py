from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas, database
from uuid import UUID

router = APIRouter()

@router.get("/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: UUID, db: Session = Depends(database.SessionLocal)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: UUID, user_update: schemas.UserCreate, db: Session = Depends(database.SessionLocal)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.full_name = user_update.full_name
    user.email = user_update.email
    user.password_hash = user_update.password  # Should hash in production
    db.commit()
    db.refresh(user)
    return user
