from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.main import app
from app.database import SessionLocal
from app.models import Transaction
from app.api.analytics import parse_month_range


client = TestClient(app)
KOLKATA_TZ = ZoneInfo("Asia/Kolkata")
MONTH = "2026-07"


def test_category_spending_analytics() -> None:
    response = client.get(f"/api/analytics/categories?month={MONTH}")
    assert response.status_code == 200, response.text
    payload = response.json()

    assert set(payload) == {"month", "items", "total_spend"}
    assert payload["month"] == MONTH
    assert payload["items"]
    categories = [item["category"] for item in payload["items"]]
    amounts = [Decimal(item["amount"]) for item in payload["items"]]
    counts = [item["transaction_count"] for item in payload["items"]]

    assert len(categories) == len(set(categories))
    assert all(amount > 0 for amount in amounts)
    assert all(count > 0 for count in counts)
    assert amounts == sorted(amounts, reverse=True)
    assert sum(amounts, start=Decimal("0")) == Decimal(payload["total_spend"])


def test_category_spending_excludes_ineligible_transactions() -> None:
    response = client.get(f"/api/analytics/categories?month={MONTH}")
    payload = response.json()
    actual = {item["category"]: (Decimal(item["amount"]), item["transaction_count"]) for item in payload["items"]}

    _, month_start, next_month_start = parse_month_range(MONTH)
    with SessionLocal() as session:
        expected_rows = session.execute(
            select(
                Transaction.category,
                func.sum(Transaction.amount),
                func.count(Transaction.id),
            )
            .where(
                Transaction.status == "SUCCESS",
                Transaction.amount > 0,
                Transaction.transaction_at >= month_start,
                Transaction.transaction_at < next_month_start,
            )
            .group_by(Transaction.category)
        ).all()
        ineligible_count = session.scalar(
            select(func.count())
            .select_from(Transaction)
            .where(
                (Transaction.status != "SUCCESS")
                | (Transaction.amount <= 0)
                | (Transaction.transaction_at < month_start)
                | (Transaction.transaction_at >= next_month_start)
            )
        )

    expected = {
        row.category: (row[1], row[2])
        for row in expected_rows
    }
    assert actual == expected
    assert ineligible_count > 0


def test_month_validation_and_no_data_month() -> None:
    assert client.get("/api/analytics/categories").status_code == 422
    for month in ("2026-7", "07-2026", "2026-00", "2026-13", "abc", ""):
        assert client.get(f"/api/analytics/categories?month={month}").status_code == 422

    no_data = client.get("/api/analytics/categories?month=2035-01")
    assert no_data.status_code == 200
    assert no_data.json() == {"month": "2035-01", "items": [], "total_spend": "0"}


def test_month_range_boundaries_and_december_rollover() -> None:
    month, start, end = parse_month_range("2025-12")
    assert month == "2025-12"
    assert start == datetime(2025, 12, 1, tzinfo=KOLKATA_TZ)
    assert end == datetime(2026, 1, 1, tzinfo=KOLKATA_TZ)

    _, july_start, august_start = parse_month_range(MONTH)
    assert july_start == datetime(2026, 7, 1, tzinfo=KOLKATA_TZ)
    assert august_start == datetime(2026, 8, 1, tzinfo=KOLKATA_TZ)
