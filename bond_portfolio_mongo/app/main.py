
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
from jose import jwt
from passlib.context import CryptContext

import uuid
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import math

app = FastAPI(title="Bond Portfolio In-Memory API", version="1.0.0")

# In-memory storage
users = []
portfolios = []

# JWT settings
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_password_hash(password):
	return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
	return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None):
	to_encode = data.copy()
	expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
	to_encode.update({"exp": expire})
	return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
	credentials_exception = HTTPException(
		status_code=401,
		detail="Could not validate credentials",
		headers={"WWW-Authenticate": "Bearer"},
	)
	try:
		payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
		user_id: str = payload.get("sub")
		if user_id is None:
			raise credentials_exception
	except Exception:
		raise credentials_exception
	user = next((u for u in users if u["id"] == user_id), None)
	if user is None:
		raise credentials_exception
	return user

# Models
class User(BaseModel):
	full_name: str
	email: str
	password: str

class UserOut(BaseModel):
	id: str
	full_name: str
	email: str


# Expanded Holding model for detailed analytics
class Holding(BaseModel):
	isin: str
	bond_name: str
	face_value: float
	coupon_rate: float
	coupon_frequency: int
	purchase_date: str
	maturity_date: str
	purchase_clean_price: float
	purchase_accrued_interest: float
	purchase_dirty_price: float
	purchase_full_price: float
	purchase_ytm: float
	sale_date: Optional[str] = None
	sale_clean_price: Optional[float] = None
	sale_accrued_interest: Optional[float] = None
	sale_dirty_price: Optional[float] = None
	sale_full_price: Optional[float] = None
	sale_ytm: Optional[float] = None
	funding_rate: Optional[float] = None
	funding_cost: Optional[float] = None
	coupons_received: Optional[float] = None
	holding_period_days: Optional[int] = None
	net_profit_loss: Optional[float] = None
	next_coupon_date: Optional[str] = None
	all_coupon_dates: Optional[List[str]] = None
	all_coupon_amounts: Optional[List[float]] = None
	macaulay_duration: Optional[float] = None
	modified_duration: Optional[float] = None
	convexity: Optional[float] = None
	market_value: Optional[float] = None
	unrealized_gain_loss: Optional[float] = None

class Portfolio(BaseModel):
	user_id: str
	portfolio_name: str
	holdings: List[Holding]

class PortfolioOut(Portfolio):
	id: str

# Auth endpoints
@app.post("/auth/register", response_model=UserOut)
def register(user: User):
	for u in users:
		if u["email"] == user.email:
			raise HTTPException(status_code=400, detail="Email already registered")
	user_dict = user.dict()
	user_dict["id"] = str(uuid.uuid4())
	user_dict["password_hash"] = get_password_hash(user.password)
	del user_dict["password"]
	users.append(user_dict)
	return {"id": user_dict["id"], "full_name": user_dict["full_name"], "email": user_dict["email"]}

@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
	user = next((u for u in users if u["email"] == form_data.username), None)
	if not user or not verify_password(form_data.password, user["password_hash"]):
		raise HTTPException(status_code=401, detail="Incorrect email or password")
	access_token = create_access_token({"sub": user["id"]})
	return {"access_token": access_token, "token_type": "bearer"}


# --- Bond Analytics Calculation Functions ---
def get_coupon_dates(purchase_date, maturity_date, frequency):
	# Returns all coupon dates from purchase_date to maturity_date
	purchase = datetime.strptime(purchase_date, "%Y-%m-%d")
	maturity = datetime.strptime(maturity_date, "%Y-%m-%d")
	months = 12 // frequency
	dates = []
	d = maturity
	while d > purchase:
		dates.append(d)
		d -= relativedelta(months=months)
	dates = sorted([dt for dt in dates if dt > purchase])
	return [dt.strftime("%Y-%m-%d") for dt in dates]

def next_coupon_date(purchase_date, maturity_date, frequency):
	dates = get_coupon_dates(purchase_date, maturity_date, frequency)
	today = datetime.today().strftime("%Y-%m-%d")
	for d in dates:
		if d > today:
			return d
	return None

def accrued_interest(face_value, coupon_rate, coupon_frequency, last_coupon_date, settlement_date):
	# Simple 30/360 day count
	last = datetime.strptime(last_coupon_date, "%Y-%m-%d")
	settle = datetime.strptime(settlement_date, "%Y-%m-%d")
	days = (settle - last).days
	period = 365 // coupon_frequency
	ai = (days / period) * (coupon_rate * face_value / coupon_frequency)
	return round(ai, 4)

def dirty_price(clean_price, accrued_interest):
	return round(clean_price + accrued_interest, 4)

def full_price(dirty_price, face_value):
	return round((dirty_price / 100) * face_value, 2)

def funding_cost(balance, funding_rate, days):
	return round(balance * funding_rate * (days / 365), 2)

def coupons_received(coupon_rate, face_value, coupon_frequency, purchase_date, sale_date):
	# Sum coupons between purchase and sale
	coupons = 0
	purchase = datetime.strptime(purchase_date, "%Y-%m-%d")
	sale = datetime.strptime(sale_date, "%Y-%m-%d")
	months = 12 // coupon_frequency
	d = purchase
	while True:
		d += relativedelta(months=months)
		if d > sale:
			break
		coupons += (coupon_rate * face_value / coupon_frequency)
	return round(coupons, 2)

def holding_period_days(purchase_date, sale_date):
	d1 = datetime.strptime(purchase_date, "%Y-%m-%d")
	d2 = datetime.strptime(sale_date, "%Y-%m-%d")
	return (d2 - d1).days

def net_profit_loss(sale_full_price, coupons_received, purchase_full_price, funding_cost):
	return round((sale_full_price + coupons_received) - (purchase_full_price + funding_cost), 2)

# --- Portfolio endpoint with calculations ---
@app.post("/portfolio", response_model=PortfolioOut)
def create_portfolio(portfolio: Portfolio, current_user: dict = Depends(get_current_user)):
	portfolio_dict = portfolio.dict()
	portfolio_dict["id"] = str(uuid.uuid4())
	# Calculate analytics for each holding
	for h in portfolio_dict["holdings"]:
		# Coupon schedule
		h["all_coupon_dates"] = get_coupon_dates(h["purchase_date"], h["maturity_date"], h["coupon_frequency"])
		h["next_coupon_date"] = next_coupon_date(h["purchase_date"], h["maturity_date"], h["coupon_frequency"])
		# Accrued interest (purchase)
		if not h.get("purchase_accrued_interest"):
			h["purchase_accrued_interest"] = accrued_interest(
				h["face_value"], h["coupon_rate"], h["coupon_frequency"],
				h["purchase_date"], h["purchase_date"]
			)
		# Dirty price (purchase)
		if not h.get("purchase_dirty_price"):
			h["purchase_dirty_price"] = dirty_price(h["purchase_clean_price"], h["purchase_accrued_interest"])
		# Full price (purchase)
		if not h.get("purchase_full_price"):
			h["purchase_full_price"] = full_price(h["purchase_dirty_price"], h["face_value"])
		# Sale analytics if sale_date provided
		if h.get("sale_date") and h.get("sale_clean_price") is not None:
			if not h.get("sale_accrued_interest"):
				h["sale_accrued_interest"] = accrued_interest(
					h["face_value"], h["coupon_rate"], h["coupon_frequency"],
					h["purchase_date"], h["sale_date"]
				)
			if not h.get("sale_dirty_price"):
				h["sale_dirty_price"] = dirty_price(h["sale_clean_price"], h["sale_accrued_interest"])
			if not h.get("sale_full_price"):
				h["sale_full_price"] = full_price(h["sale_dirty_price"], h["face_value"])
			# Coupons received
			h["coupons_received"] = coupons_received(
				h["coupon_rate"], h["face_value"], h["coupon_frequency"],
				h["purchase_date"], h["sale_date"]
			)
			# Holding period
			h["holding_period_days"] = holding_period_days(h["purchase_date"], h["sale_date"])
			# Funding cost
			if h.get("funding_rate") is not None:
				h["funding_cost"] = funding_cost(h["purchase_full_price"], h["funding_rate"], h["holding_period_days"])
			# Net P/L
			h["net_profit_loss"] = net_profit_loss(
				h["sale_full_price"], h["coupons_received"], h["purchase_full_price"], h.get("funding_cost", 0)
			)
	portfolios.append(portfolio_dict)
	return portfolio_dict

@app.get("/portfolio", response_model=List[PortfolioOut])
def get_user_portfolios(current_user: dict = Depends(get_current_user)):
	user_portfolios = [p for p in portfolios if p["user_id"] == current_user["id"]]
	return user_portfolios

@app.get("/portfolio/{portfolio_id}", response_model=PortfolioOut)
def get_portfolio(portfolio_id: str, current_user: dict = Depends(get_current_user)):
	portfolio = next((p for p in portfolios if p["id"] == portfolio_id and p["user_id"] == current_user["id"]), None)
	if not portfolio:
		raise HTTPException(status_code=404, detail="Portfolio not found")
	return portfolio
