import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Numeric, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(150))
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(Boolean, default=True)
    portfolios = relationship("Portfolio", back_populates="user")

class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    portfolio_name = Column(String(150))
    upload_date = Column(DateTime, default=datetime.utcnow)
    total_book_value = Column(Numeric(18,2))
    total_market_value = Column(Numeric(18,2))
    weighted_ytm = Column(Numeric(8,4))
    weighted_duration = Column(Numeric(8,4))
    weighted_modified_duration = Column(Numeric(8,4))
    total_dv01 = Column(Numeric(18,4))
    is_current = Column(Boolean, default=True)
    user = relationship("User", back_populates="portfolios")
    holdings = relationship("Holding", back_populates="portfolio")
    scenarios = relationship("ScenarioAnalysis", back_populates="portfolio")

class Holding(Base):
    __tablename__ = "holdings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"))
    isin = Column(String(20))
    bond_name = Column(String(200))
    issuer = Column(String(150))
    bond_type = Column(String(50))
    face_value = Column(Numeric(18,2))
    coupon_rate = Column(Numeric(8,4))
    coupon_frequency = Column(Integer)
    issue_date = Column(DateTime)
    maturity_date = Column(DateTime)
    clean_price = Column(Numeric(10,4))
    accrued_interest = Column(Numeric(10,4))
    dirty_price = Column(Numeric(10,4))
    ytm = Column(Numeric(8,4))
    macaulay_duration = Column(Numeric(8,4))
    modified_duration = Column(Numeric(8,4))
    convexity = Column(Numeric(12,6))
    market_value = Column(Numeric(18,2))
    unrealized_gain_loss = Column(Numeric(18,2))
    portfolio = relationship("Portfolio", back_populates="holdings")

class ScenarioAnalysis(Base):
    __tablename__ = "scenario_analysis"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"))
    shock_bps = Column(Integer)
    shocked_value = Column(Numeric(18,2))
    impact = Column(Numeric(18,2))
    created_at = Column(DateTime, default=datetime.utcnow)
    portfolio = relationship("Portfolio", back_populates="scenarios")
