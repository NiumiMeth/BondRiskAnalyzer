from fastapi import FastAPI
from app.routers import auth, users, portfolios, holdings, analytics

app = FastAPI(title="Bond Portfolio Banking API", version="1.0.0")

# Routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(portfolios.router, prefix="/portfolios", tags=["portfolios"])
app.include_router(holdings.router, prefix="/holdings", tags=["holdings"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
