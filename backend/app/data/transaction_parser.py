"""Parsing and normalization for source transaction JSON files.

This module deliberately has no database or SQLAlchemy dependencies.  It turns
raw JSON-compatible values into typed records ready for a later seed layer.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo


KOLKATA_TZ = ZoneInfo("Asia/Kolkata")
ALLOWED_STATUSES = frozenset({"SUCCESS", "FAILED", "PENDING"})
TimestampFormat = Literal["iso", "date_only", "ddmmyyyy", "epoch_milliseconds"]


class TransactionParseError(ValueError):
    """Raised when one raw transaction cannot be normalized safely."""

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        value: Any = None,
        record_index: int | None = None,
        transaction_id: Any = None,
    ) -> None:
        context: list[str] = []
        if record_index is not None:
            context.append(f"record_index={record_index}")
        if transaction_id is not None:
            context.append(f"transaction_id={transaction_id!r}")
        if field is not None:
            context.append(f"field={field!r}")
        if field is not None:
            context.append(f"value={value!r}")
        suffix = f" ({', '.join(context)})" if context else ""
        super().__init__(f"{message}{suffix}")


@dataclass(frozen=True, slots=True)
class NormalizedTransaction:
    transaction_id: str
    transaction_at: datetime
    merchant: str
    category: str
    amount: Decimal
    currency: str
    status: str
    payment_method: str


@dataclass(slots=True)
class DataQualityReport:
    """Statistics measured from a parsed source file.

    ``duplicate_transaction_id_count`` is the number of rows beyond the first
    occurrence of each transaction ID; duplicate rows remain in the output.
    """

    total_records: int = 0
    normalized_records: int = 0
    missing_category_count: int = 0
    null_category_count: int = 0
    blank_category_count: int = 0
    numeric_string_amount_count: int = 0
    negative_amount_count: int = 0
    lowercase_or_noncanonical_status_count: int = 0
    epoch_timestamp_count: int = 0
    date_only_timestamp_count: int = 0
    ddmmyyyy_timestamp_count: int = 0
    iso_timestamp_count: int = 0
    duplicate_transaction_id_count: int = 0
    unique_transaction_ids: int = 0
    categories: set[str] = field(default_factory=set)
    statuses: set[str] = field(default_factory=set)
    payment_methods: set[str] = field(default_factory=set)
    currencies: set[str] = field(default_factory=set)


def _error(
    message: str,
    *,
    field: str,
    value: Any,
    record_index: int | None,
    raw: Mapping[str, Any],
) -> TransactionParseError:
    return TransactionParseError(
        message,
        field=field,
        value=value,
        record_index=record_index,
        transaction_id=raw.get("id"),
    )


def _required_string(
    raw: Mapping[str, Any], field: str, record_index: int | None
) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not (normalized := value.strip()):
        raise _error(
            "Required string field is missing or blank",
            field=field,
            value=value,
            record_index=record_index,
            raw=raw,
        )
    return normalized


def _normalize_category(raw: Mapping[str, Any], record_index: int | None) -> str:
    if "category" not in raw:
        return "Uncategorized"

    value = raw["category"]
    if value is None:
        return "Uncategorized"
    if not isinstance(value, str):
        raise _error(
            "Category must be a string or null",
            field="category",
            value=value,
            record_index=record_index,
            raw=raw,
        )
    return value.strip() or "Uncategorized"


def _normalize_amount(raw: Mapping[str, Any], record_index: int | None) -> Decimal:
    value = raw.get("amount")
    if value is None:
        raise _error(
            "Amount is required",
            field="amount",
            value=value,
            record_index=record_index,
            raw=raw,
        )
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise _error(
            "Amount is not a valid Decimal",
            field="amount",
            value=value,
            record_index=record_index,
            raw=raw,
        ) from exc
    if not amount.is_finite():
        raise _error(
            "Amount must be a finite Decimal",
            field="amount",
            value=value,
            record_index=record_index,
            raw=raw,
        )
    return amount


def _normalize_status(raw: Mapping[str, Any], record_index: int | None) -> str:
    source_status = _required_string(raw, "status", record_index)
    status = source_status.upper()
    if status not in ALLOWED_STATUSES:
        raise _error(
            "Status is not one of SUCCESS, FAILED, or PENDING",
            field="status",
            value=raw.get("status"),
            record_index=record_index,
            raw=raw,
        )
    return status


def _parse_timestamp(
    raw: Mapping[str, Any], record_index: int | None
) -> tuple[datetime, TimestampFormat]:
    value = raw.get("timestamp")
    if isinstance(value, bool) or value is None:
        raise _error(
            "Timestamp is required",
            field="timestamp",
            value=value,
            record_index=record_index,
            raw=raw,
        )

    if (isinstance(value, int) or (isinstance(value, float) and value.is_integer())) or (
        isinstance(value, str) and value.strip().isdigit()
    ):
        try:
            return (
                datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc),
                "epoch_milliseconds",
            )
        except (OverflowError, OSError, ValueError) as exc:
            raise _error(
                "Epoch timestamp milliseconds are out of range",
                field="timestamp",
                value=value,
                record_index=record_index,
                raw=raw,
            ) from exc

    if not isinstance(value, str) or not (timestamp := value.strip()):
        raise _error(
            "Timestamp must be a non-blank string or epoch milliseconds",
            field="timestamp",
            value=value,
            record_index=record_index,
            raw=raw,
        )

    try:
        if len(timestamp) == 10:
            date_value = datetime.strptime(timestamp, "%Y-%m-%d").date()
            return datetime.combine(date_value, time.min, tzinfo=KOLKATA_TZ), "date_only"

        if "/" in timestamp:
            local_value = datetime.strptime(timestamp, "%d/%m/%Y %H:%M:%S")
            return local_value.replace(tzinfo=KOLKATA_TZ), "ddmmyyyy"

        iso_value = datetime.fromisoformat(
            f"{timestamp[:-1]}+00:00" if timestamp.endswith("Z") else timestamp
        )
    except ValueError as exc:
        raise _error(
            "Timestamp does not match a supported format",
            field="timestamp",
            value=value,
            record_index=record_index,
            raw=raw,
        ) from exc

    if iso_value.tzinfo is None or iso_value.utcoffset() is None:
        raise _error(
            "ISO timestamp must include a timezone offset",
            field="timestamp",
            value=value,
            record_index=record_index,
            raw=raw,
        )
    return iso_value, "iso"


def normalize_transaction(
    raw: Mapping[str, Any], *, record_index: int | None = None
) -> NormalizedTransaction:
    """Validate and normalize one raw JSON transaction record."""
    if not isinstance(raw, Mapping):
        raise TransactionParseError(
            "Transaction record must be an object",
            field="record",
            value=raw,
            record_index=record_index,
        )

    transaction_id = _required_string(raw, "id", record_index)
    transaction_at, _ = _parse_timestamp(raw, record_index)
    return NormalizedTransaction(
        transaction_id=transaction_id,
        transaction_at=transaction_at,
        merchant=_required_string(raw, "merchant", record_index),
        category=_normalize_category(raw, record_index),
        amount=_normalize_amount(raw, record_index),
        currency=_required_string(raw, "currency", record_index).upper(),
        status=_normalize_status(raw, record_index),
        payment_method=_required_string(raw, "payment_method", record_index),
    )


def _update_report(
    report: DataQualityReport,
    raw: Mapping[str, Any],
    transaction: NormalizedTransaction,
    timestamp_format: TimestampFormat,
    seen_transaction_ids: set[str],
) -> None:
    category = raw.get("category")
    if "category" not in raw:
        report.missing_category_count += 1
    elif category is None:
        report.null_category_count += 1
    elif isinstance(category, str) and not category.strip():
        report.blank_category_count += 1

    if isinstance(raw.get("amount"), str):
        report.numeric_string_amount_count += 1
    if transaction.amount < 0:
        report.negative_amount_count += 1
    if raw.get("status") != transaction.status:
        report.lowercase_or_noncanonical_status_count += 1

    timestamp_count_field = {
        "iso": "iso_timestamp_count",
        "date_only": "date_only_timestamp_count",
        "ddmmyyyy": "ddmmyyyy_timestamp_count",
        "epoch_milliseconds": "epoch_timestamp_count",
    }[timestamp_format]
    setattr(report, timestamp_count_field, getattr(report, timestamp_count_field) + 1)

    if transaction.transaction_id in seen_transaction_ids:
        report.duplicate_transaction_id_count += 1
    else:
        seen_transaction_ids.add(transaction.transaction_id)

    report.categories.add(transaction.category)
    report.statuses.add(transaction.status)
    report.payment_methods.add(transaction.payment_method)
    report.currencies.add(transaction.currency)


def parse_transactions(path: Path) -> tuple[list[NormalizedTransaction], DataQualityReport]:
    """Load, validate, and normalize every transaction in a JSON array."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TransactionParseError(f"Unable to read transaction JSON: {exc}") from exc

    if not isinstance(payload, list):
        raise TransactionParseError("Transaction JSON root must be an array", value=payload)

    records: list[NormalizedTransaction] = []
    report = DataQualityReport(total_records=len(payload))
    seen_transaction_ids: set[str] = set()

    for record_index, raw in enumerate(payload):
        transaction = normalize_transaction(raw, record_index=record_index)
        _, timestamp_format = _parse_timestamp(raw, record_index)
        records.append(transaction)
        _update_report(report, raw, transaction, timestamp_format, seen_transaction_ids)

    report.normalized_records = len(records)
    report.unique_transaction_ids = len(seen_transaction_ids)
    return records, report


def format_report(report: DataQualityReport) -> str:
    """Format a concise, human-readable parser report."""
    return "\n".join(
        (
            f"Total records: {report.total_records}",
            f"Normalized records: {report.normalized_records}",
            f"Missing categories: {report.missing_category_count}",
            f"Null categories: {report.null_category_count}",
            f"Blank categories: {report.blank_category_count}",
            f"Numeric string amounts: {report.numeric_string_amount_count}",
            f"Negative amounts: {report.negative_amount_count}",
            f"Normalized statuses: {report.lowercase_or_noncanonical_status_count}",
            f"Duplicate transaction IDs: {report.duplicate_transaction_id_count}",
            "Timestamp formats:",
            f"  ISO: {report.iso_timestamp_count}",
            f"  Date only: {report.date_only_timestamp_count}",
            f"  DD/MM/YYYY: {report.ddmmyyyy_timestamp_count}",
            f"  Epoch milliseconds: {report.epoch_timestamp_count}",
            f"Currencies: {sorted(report.currencies)}",
            f"Statuses: {sorted(report.statuses)}",
            f"Payment methods: {sorted(report.payment_methods)}",
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize a Spendly transaction JSON file.")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "data" / "transactions.json",
    )
    args = parser.parse_args()
    try:
        _, report = parse_transactions(args.path)
    except TransactionParseError as exc:
        parser.error(str(exc))
    print(format_report(report))


if __name__ == "__main__":
    main()
