from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.analytics import router as analytics_router
from app.api.rewards import router as rewards_router
from app.api.transactions import router as transactions_router
from app.database import engine
from app.config import settings

app = FastAPI(
    title="Spendly API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(transactions_router)
app.include_router(analytics_router)
app.include_router(rewards_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/db-check")
def db_check():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT current_database(), version();"))
        row = result.fetchone()

    return {
        "database": row[0],
        "version": row[1],
    }
