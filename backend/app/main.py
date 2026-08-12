from fastapi import FastAPI
from sqlalchemy import text

from app.api.transactions import router as transactions_router
from app.database import engine

app = FastAPI(
    title="Spendly API",
    version="1.0.0",
)

app.include_router(transactions_router)


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
