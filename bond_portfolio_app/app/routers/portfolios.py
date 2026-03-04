from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app import models, schemas, database
from uuid import UUID, uuid4
from typing import List
from datetime import datetime

router = APIRouter()

@router.post("/upload", response_model=schemas.PortfolioOut)
def upload_portfolio(file: UploadFile = File(...), db: Session = Depends(database.SessionLocal)):
    # Placeholder: parse Excel, calculate metrics, insert portfolio/holdings
    new_portfolio = models.Portfolio(id=uuid4(), portfolio_name=file.filename, upload_date=datetime.utcnow())
    db.add(new_portfolio)
    db.commit()
    db.refresh(new_portfolio)
    return new_portfolio

@router.get("/", response_model=List[schemas.PortfolioOut])
def get_portfolios(db: Session = Depends(database.SessionLocal)):
    return db.query(models.Portfolio).all()

@router.get("/{portfolio_id}", response_model=schemas.PortfolioOut)
def get_portfolio(portfolio_id: UUID, db: Session = Depends(database.SessionLocal)):
    portfolio = db.query(models.Portfolio).filter(models.Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio

@router.delete("/{portfolio_id}")
def delete_portfolio(portfolio_id: UUID, db: Session = Depends(database.SessionLocal)):
    portfolio = db.query(models.Portfolio).filter(models.Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    db.delete(portfolio)
    db.commit()
    return {"detail": "Portfolio deleted"}
