from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
KOLKATA_TZ = ZoneInfo("Asia/Kolkata")


def get(path: str = "/api/transactions") -> dict:
    response = client.get(path)
    assert response.status_code == 200, response.text
    return response.json()


def test_transaction_metadata() -> None:
    payload = get("/api/transactions/metadata")

    assert set(payload) == {"categories", "statuses", "payment_methods"}
    for values in payload.values():
        assert all(isinstance(value, str) for value in values)
        assert values == sorted(values)
        assert len(values) == len(set(values))

    assert "Uncategorized" in payload["categories"]
    assert {"SUCCESS", "FAILED", "PENDING"}.issubset(payload["statuses"])
    assert {"Credit Card", "Debit Card", "Netbanking", "UPI"}.issubset(
        payload["payment_methods"]
    )


def test_default_listing_and_pagination() -> None:
    payload = get()
    assert payload["page"] == 1
    assert payload["page_size"] == 50
    assert len(payload["items"]) == 50
    assert payload["total"] == 10_000
    assert payload["total_pages"] == 200

    page_two = get("/api/transactions?page=2&page_size=25")
    assert page_two["page"] == 2
    assert page_two["page_size"] == 25
    assert len(page_two["items"]) <= 25


def test_search_category_and_status_filters() -> None:
    for search in ("Swiggy", "swiggy"):
        payload = get(f"/api/transactions?search={search}")
        assert payload["total"] > 0
        assert all(search.lower() in item["merchant"].lower() for item in payload["items"])

    shopping = get("/api/transactions?category=Shopping")
    assert shopping["total"] > 0
    assert all(item["category"] == "Shopping" for item in shopping["items"])

    failed = get("/api/transactions?status=FAILED")
    assert failed["total"] > 0
    assert all(item["status"] == "FAILED" for item in failed["items"])


def test_date_and_amount_filters() -> None:
    dates = get("/api/transactions?date_from=2025-01-01&date_to=2026-12-31")
    for item in dates["items"]:
        local_date = datetime.fromisoformat(item["transaction_at"]).astimezone(KOLKATA_TZ).date()
        assert datetime(2025, 1, 1).date() <= local_date <= datetime(2026, 12, 31).date()

    amounts = get("/api/transactions?amount_min=100&amount_max=500")
    assert amounts["total"] > 0
    assert all(Decimal("100") <= Decimal(item["amount"]) <= Decimal("500") for item in amounts["items"])

    negative = get("/api/transactions?amount_min=-100000&amount_max=-0.01")
    assert negative["total"] > 0
    assert all(Decimal(item["amount"]) < 0 for item in negative["items"])


def test_sorting() -> None:
    for order in ("asc", "desc"):
        payload = get(f"/api/transactions?sort_by=amount&sort_order={order}")
        amounts = [Decimal(item["amount"]) for item in payload["items"]]
        assert amounts == sorted(amounts, reverse=order == "desc")

        dates = get(f"/api/transactions?sort_by=date&sort_order={order}")
        values = [datetime.fromisoformat(item["transaction_at"]) for item in dates["items"]]
        assert values == sorted(values, reverse=order == "desc")


def test_validation_and_empty_results() -> None:
    for path in (
        "/api/transactions?page=0",
        "/api/transactions?page_size=101",
        "/api/transactions?status=UNKNOWN",
        "/api/transactions?date_from=2026-02-01&date_to=2026-01-01",
        "/api/transactions?amount_min=500&amount_max=100",
    ):
        assert client.get(path).status_code == 422

    payload = get("/api/transactions?search=no-such-merchant")
    assert payload == {"items": [], "page": 1, "page_size": 50, "total": 0, "total_pages": 0}
