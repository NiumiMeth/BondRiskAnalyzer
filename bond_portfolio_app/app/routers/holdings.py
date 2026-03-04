from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas, database
from uuid import UUID
from typing import List

router = APIRouter()

@router.get("/portfolios/{portfolio_id}/holdings", response_model=List[schemas.HoldingOut])
def get_holdings(portfolio_id: UUID, db: Session = Depends(database.SessionLocal)):
    holdings = db.query(models.Holding).filter(models.Holding.portfolio_id == portfolio_id).all()
    return holdings

@router.get("/{holding_id}", response_model=schemas.HoldingOut)
def get_holding(holding_id: UUID, db: Session = Depends(database.SessionLocal)):
    holding = db.query(models.Holding).filter(models.Holding.id == holding_id).first()
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    return holding
