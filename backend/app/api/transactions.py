from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Transaction
from app.schemas.transaction import PaginatedTransactions, TransactionResponse


router = APIRouter(prefix="/api/transactions", tags=["transactions"])

KOLKATA_TZ = ZoneInfo("Asia/Kolkata")
SortBy = Literal["date", "amount"]
SortOrder = Literal["asc", "desc"]
TransactionStatus = Literal["SUCCESS", "FAILED", "PENDING"]


@router.get("", response_model=PaginatedTransactions)
def list_transactions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    search: str | None = None,
    category: str | None = None,
    status: TransactionStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    amount_min: Decimal | None = None,
    amount_max: Decimal | None = None,
    sort_by: SortBy = "date",
    sort_order: SortOrder = "desc",
    db: Session = Depends(get_db),
) -> PaginatedTransactions:
    """Return a filtered, paginated view of the seeded transaction data."""
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=422,
            detail="date_from must be before or equal to date_to",
        )
    if amount_min is not None and amount_max is not None and amount_min > amount_max:
        raise HTTPException(
            status_code=422,
            detail="amount_min must be less than or equal to amount_max",
        )

    conditions = []
    if search is not None and (trimmed_search := search.strip()):
        conditions.append(Transaction.merchant.ilike(f"%{trimmed_search}%"))
    if category is not None:
        conditions.append(Transaction.category == category)
    if status is not None:
        conditions.append(Transaction.status == status)
    if date_from is not None:
        conditions.append(
            Transaction.transaction_at
            >= datetime.combine(date_from, time.min, tzinfo=KOLKATA_TZ)
        )
    if date_to is not None:
        conditions.append(
            Transaction.transaction_at
            < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=KOLKATA_TZ)
        )
    if amount_min is not None:
        conditions.append(Transaction.amount >= amount_min)
    if amount_max is not None:
        conditions.append(Transaction.amount <= amount_max)

    sort_column = {
        "date": Transaction.transaction_at,
        "amount": Transaction.amount,
    }[sort_by]
    ordering = (
        (sort_column.asc(), Transaction.id.asc())
        if sort_order == "asc"
        else (sort_column.desc(), Transaction.id.desc())
    )

    total = db.scalar(select(func.count()).select_from(Transaction).where(*conditions))
    transactions = db.scalars(
        select(Transaction)
        .where(*conditions)
        .order_by(*ordering)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return PaginatedTransactions(
        items=[TransactionResponse.model_validate(transaction) for transaction in transactions],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )
