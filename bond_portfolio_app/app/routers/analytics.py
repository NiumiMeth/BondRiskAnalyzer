from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas, database
from uuid import UUID
from typing import List

router = APIRouter()

@router.get("/portfolios/{portfolio_id}/summary")
def portfolio_summary(portfolio_id: UUID, db: Session = Depends(database.SessionLocal)):
    portfolio = db.query(models.Portfolio).filter(models.Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return {
        "total_book_value": portfolio.total_book_value,
        "total_market_value": portfolio.total_market_value,
        "weighted_ytm": portfolio.weighted_ytm,
        "weighted_duration": portfolio.weighted_duration,
        "modified_duration": portfolio.weighted_modified_duration,
        "total_dv01": portfolio.total_dv01
    }

@router.post("/portfolios/{portfolio_id}/shock")
def yield_shock(portfolio_id: UUID, shock_bps: int, db: Session = Depends(database.SessionLocal)):
    # Placeholder: calculate shocked value
    return {"shocked_value": 0, "impact": 0}

@router.get("/portfolios/{portfolio_id}/cashflows")
def cashflows(portfolio_id: UUID, db: Session = Depends(database.SessionLocal)):
    # Placeholder: return future coupon payments
    return []
