from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    created_at: datetime
    status: bool
    class Config:
        orm_mode = True

class PortfolioBase(BaseModel):
    portfolio_name: str
    total_book_value: Optional[float]
    total_market_value: Optional[float]
    weighted_ytm: Optional[float]
    weighted_duration: Optional[float]
    weighted_modified_duration: Optional[float]
    total_dv01: Optional[float]
    is_current: Optional[bool]

class PortfolioCreate(PortfolioBase):
    pass

class PortfolioOut(PortfolioBase):
    id: UUID
    upload_date: datetime
    class Config:
        orm_mode = True

class HoldingBase(BaseModel):
    isin: str
    bond_name: str
    issuer: Optional[str]
    bond_type: Optional[str]
    face_value: float
    coupon_rate: float
    coupon_frequency: int
    issue_date: Optional[datetime]
    maturity_date: datetime
    clean_price: float
    accrued_interest: float
    dirty_price: float
    ytm: float
    macaulay_duration: float
    modified_duration: float
    convexity: float
    market_value: float
    unrealized_gain_loss: float

class HoldingCreate(HoldingBase):
    pass

class HoldingOut(HoldingBase):
    id: UUID
    class Config:
        orm_mode = True

class ScenarioAnalysisBase(BaseModel):
    shock_bps: int
    shocked_value: float
    impact: float

class ScenarioAnalysisCreate(ScenarioAnalysisBase):
    pass

class ScenarioAnalysisOut(ScenarioAnalysisBase):
    id: UUID
    created_at: datetime
    class Config:
        orm_mode = True
