from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path

import pytest

from app.data.transaction_parser import (
    KOLKATA_TZ,
    TransactionParseError,
    normalize_transaction,
    parse_transactions,
)


def raw_transaction(**overrides: object) -> dict[str, object]:
    transaction: dict[str, object] = {
        "id": "TXN-1",
        "timestamp": "2025-10-03T21:03:27Z",
        "merchant": "Example Shop",
        "category": "Shopping",
        "amount": 912.62,
        "currency": "inr",
        "status": "SUCCESS",
        "payment_method": "UPI",
    }
    transaction.update(overrides)
    return transaction


def test_iso_z_timestamp_is_timezone_aware() -> None:
    transaction = normalize_transaction(raw_transaction())
    assert transaction.transaction_at == datetime(2025, 10, 3, 21, 3, 27, tzinfo=timezone.utc)


def test_iso_offset_timestamp_is_timezone_aware() -> None:
    transaction = normalize_transaction(
        raw_transaction(timestamp="2026-03-25T06:08:03+05:30")
    )
    assert transaction.transaction_at.utcoffset().total_seconds() == 19_800


def test_date_only_timestamp_is_kolkata_midnight() -> None:
    transaction = normalize_transaction(raw_transaction(timestamp="2025-12-29"))
    assert transaction.transaction_at == datetime(2025, 12, 29, tzinfo=KOLKATA_TZ)


def test_ddmmyyyy_timestamp_is_kolkata_time() -> None:
    transaction = normalize_transaction(raw_transaction(timestamp="08/09/2025 12:14:32"))
    assert transaction.transaction_at == datetime(2025, 9, 8, 12, 14, 32, tzinfo=KOLKATA_TZ)


def test_epoch_milliseconds_timestamp_is_timezone_aware() -> None:
    transaction = normalize_transaction(raw_transaction(timestamp=1768265109000))
    assert transaction.transaction_at.tzinfo is not None
    assert transaction.transaction_at == datetime.fromtimestamp(1768265109, tz=timezone.utc)


def test_numeric_string_amount_uses_decimal() -> None:
    transaction = normalize_transaction(raw_transaction(amount="5065.00"))
    assert transaction.amount == Decimal("5065.00")


def test_negative_amount_is_preserved() -> None:
    transaction = normalize_transaction(raw_transaction(amount=-477.46))
    assert transaction.amount == Decimal("-477.46")


@pytest.mark.parametrize("category", [pytest.param(None), pytest.param(""), pytest.param("   ")])
def test_null_or_blank_category_becomes_uncategorized(category: object) -> None:
    transaction = normalize_transaction(raw_transaction(category=category))
    assert transaction.category == "Uncategorized"


def test_missing_category_becomes_uncategorized() -> None:
    raw = raw_transaction()
    del raw["category"]
    assert normalize_transaction(raw).category == "Uncategorized"


def test_lowercase_status_is_normalized() -> None:
    assert normalize_transaction(raw_transaction(status="success")).status == "SUCCESS"


def test_invalid_status_raises_clear_parser_error() -> None:
    with pytest.raises(TransactionParseError, match="Status is not one of"):
        normalize_transaction(raw_transaction(status="CANCELLED"), record_index=7)


def test_duplicates_are_retained_and_reported(tmp_path: Path) -> None:
    raw_records = [
        raw_transaction(id="A"),
        raw_transaction(id="A", merchant="Another Shop"),
        raw_transaction(id="B"),
        raw_transaction(id="B", merchant="Third Shop"),
        raw_transaction(id="B", merchant="Fourth Shop"),
    ]
    source = tmp_path / "transactions.json"
    source.write_text(json.dumps(raw_records), encoding="utf-8")

    records, report = parse_transactions(source)

    assert [record.transaction_id for record in records] == ["A", "A", "B", "B", "B"]
    assert report.normalized_records == 5
    assert report.unique_transaction_ids == 2
    assert report.duplicate_transaction_id_count == 3
