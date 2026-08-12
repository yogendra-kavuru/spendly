from datetime import datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Transaction
from app.schemas.analytics import CategorySpendItem, CategorySpendResponse


router = APIRouter(prefix="/api/analytics", tags=["analytics"])
KOLKATA_TZ = ZoneInfo("Asia/Kolkata")


def parse_month_range(month: str) -> tuple[str, datetime, datetime]:
    """Return a normalized month and its Kolkata-local half-open time range."""
    try:
        parsed_month = datetime.strptime(month, "%Y-%m")
    except ValueError as exc:
        raise ValueError("month must use YYYY-MM format") from exc

    normalized_month = parsed_month.strftime("%Y-%m")
    if month != normalized_month:
        raise ValueError("month must use YYYY-MM format")

    month_start = datetime.combine(parsed_month.date().replace(day=1), time.min, KOLKATA_TZ)
    if parsed_month.month == 12:
        next_month_start = month_start.replace(year=parsed_month.year + 1, month=1)
    else:
        next_month_start = month_start.replace(month=parsed_month.month + 1)
    return normalized_month, month_start, next_month_start


@router.get("/categories", response_model=CategorySpendResponse)
def get_category_spending(
    month: str = Query(..., description="Calendar month in YYYY-MM format"),
    db: Session = Depends(get_db),
) -> CategorySpendResponse:
    """Aggregate positive successful spending by category for one local month."""
    try:
        normalized_month, month_start, next_month_start = parse_month_range(month)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    category_total = func.sum(Transaction.amount).label("amount")
    transaction_count = func.count(Transaction.id).label("transaction_count")
    rows = db.execute(
        select(Transaction.category, category_total, transaction_count)
        .where(
            Transaction.status == "SUCCESS",
            Transaction.amount > 0,
            Transaction.transaction_at >= month_start,
            Transaction.transaction_at < next_month_start,
        )
        .group_by(Transaction.category)
        .order_by(category_total.desc(), Transaction.category.asc())
    ).all()

    items = [
        CategorySpendItem(
            category=row.category,
            amount=row.amount,
            transaction_count=row.transaction_count,
        )
        for row in rows
    ]
    total_spend = sum((item.amount for item in items), start=Decimal("0"))
    return CategorySpendResponse(
        month=normalized_month,
        items=items,
        total_spend=total_spend,
    )
