from fastapi import FastAPI
from app.routers import auth, portfolios

app = FastAPI(title="Bond Portfolio Mongo API", version="1.0.0")

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(portfolios.router, prefix="/portfolios", tags=["portfolios"])
