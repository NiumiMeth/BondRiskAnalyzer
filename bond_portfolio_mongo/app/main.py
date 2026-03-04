
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
from jose import jwt
from passlib.context import CryptContext
import uuid
from datetime import datetime, timedelta

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

class Holding(BaseModel):
	isin: str
	bond_name: str
	face_value: float
	coupon_rate: float
	coupon_frequency: int
	maturity_date: str
	clean_price: float
	ytm: float
	macaulay_duration: float
	modified_duration: float
	convexity: float
	market_value: float
	unrealized_gain_loss: float

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

# Portfolio endpoints
@app.post("/portfolio", response_model=PortfolioOut)
def create_portfolio(portfolio: Portfolio, current_user: dict = Depends(get_current_user)):
	portfolio_dict = portfolio.dict()
	portfolio_dict["id"] = str(uuid.uuid4())
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
