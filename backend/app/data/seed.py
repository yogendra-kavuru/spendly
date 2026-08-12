"""Idempotent development seed command for the Spendly PostgreSQL database."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, insert, select, text
from sqlalchemy.orm import Session

from app.data.transaction_parser import (
    DataQualityReport,
    NormalizedTransaction,
    format_report,
    parse_transactions,
)
from app.database import SessionLocal
from app.models import Redemption, Reward, RewardWallet, Transaction, User


DEMO_USER_NAME = "Demo User"
DEMO_INITIAL_WALLET_BALANCE = 1500
COIN_DIVISOR = Decimal("100")
MAX_COINS_PER_TRANSACTION = 100
DEFAULT_SOURCE_PATH = Path(__file__).resolve().parents[2] / "data" / "transactions.json"
# The attached dataset in this workspace is nested under ``backend/data``.
ATTACHED_SOURCE_PATH = Path(__file__).resolve().parents[2] / "backend" / "data" / "transactions.json"

REWARD_CATALOG: tuple[dict[str, object], ...] = (
    {
        "name": "₹50 Cashback",
        "description": "Get ₹50 cashback on your next eligible payment.",
        "coin_cost": 500,
        "reward_type": "CASHBACK",
        "reward_value": Decimal("50.00"),
        "active": True,
    },
    {
        "name": "Amazon ₹100 Voucher",
        "description": "Redeem a ₹100 Amazon shopping voucher.",
        "coin_cost": 900,
        "reward_type": "VOUCHER",
        "reward_value": Decimal("100.00"),
        "active": True,
    },
    {
        "name": "Swiggy ₹150 Voucher",
        "description": "Redeem a ₹150 Swiggy food voucher.",
        "coin_cost": 1200,
        "reward_type": "VOUCHER",
        "reward_value": Decimal("150.00"),
        "active": True,
    },
    {
        "name": "BookMyShow ₹200 Voucher",
        "description": "Redeem a ₹200 BookMyShow entertainment voucher.",
        "coin_cost": 1600,
        "reward_type": "VOUCHER",
        "reward_value": Decimal("200.00"),
        "active": True,
    },
    {
        "name": "₹250 Cashback",
        "description": "Get ₹250 cashback on your next eligible payment.",
        "coin_cost": 2000,
        "reward_type": "CASHBACK",
        "reward_value": Decimal("250.00"),
        "active": True,
    },
)


class SeedValidationError(RuntimeError):
    """Raised if persisted seed data does not match the parsed source data."""


@dataclass(frozen=True, slots=True)
class SeedSummary:
    demo_user_id: int
    transactions_inserted: int
    rewards_inserted: int
    wallet_balance: int
    historical_eligible_coins: int
    transactions_earning_coins: int
    uncategorized_transaction_count: int
    report: DataQualityReport


def calculate_transaction_coins(status: str, amount: Decimal) -> int:
    """Return reward coins earned by one normalized transaction."""
    if status != "SUCCESS" or amount <= 0:
        return 0
    return min(int(amount // COIN_DIVISOR), MAX_COINS_PER_TRANSACTION)


def _transaction_mappings(
    transactions: list[NormalizedTransaction], user_id: int
) -> list[dict[str, object]]:
    return [
        {
            "transaction_id": transaction.transaction_id,
            "user_id": user_id,
            "transaction_at": transaction.transaction_at,
            "merchant": transaction.merchant,
            "category": transaction.category,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "status": transaction.status,
            "payment_method": transaction.payment_method,
        }
        for transaction in transactions
    ]


def _validate_seed(
    session: Session,
    *,
    demo_user_id: int,
    source_record_count: int,
    expected_wallet_balance: int,
    expected_duplicate_count: int,
) -> None:
    counts = {
        "users": session.scalar(select(func.count()).select_from(User)),
        "transactions": session.scalar(select(func.count()).select_from(Transaction)),
        "reward_wallets": session.scalar(
            select(func.count()).select_from(RewardWallet)
        ),
        "rewards": session.scalar(select(func.count()).select_from(Reward)),
        "redemptions": session.scalar(select(func.count()).select_from(Redemption)),
    }
    expected_counts = {
        "users": 1,
        "transactions": source_record_count,
        "reward_wallets": 1,
        "rewards": len(REWARD_CATALOG),
        "redemptions": 0,
    }
    if counts != expected_counts:
        raise SeedValidationError(
            f"Seed row counts do not match expectations: {counts!r}"
        )

    wallet = session.get(RewardWallet, demo_user_id)
    if wallet is None or wallet.balance != expected_wallet_balance:
        raise SeedValidationError("Seeded wallet balance does not match calculated coins")

    transaction_count = counts["transactions"]
    unique_transaction_ids = session.scalar(
        select(func.count(func.distinct(Transaction.transaction_id)))
    )
    duplicate_count = transaction_count - unique_transaction_ids
    if duplicate_count != expected_duplicate_count:
        raise SeedValidationError(
            "Persisted duplicate transaction ID count does not match the source"
        )


def _resolve_source_path(source_path: Path | None) -> Path:
    if source_path is not None:
        return source_path
    if DEFAULT_SOURCE_PATH.exists():
        return DEFAULT_SOURCE_PATH
    return ATTACHED_SOURCE_PATH


def seed_database(source_path: Path | None = None) -> SeedSummary:
    """Reset and recreate all demo application data in one database transaction."""
    transactions, report = parse_transactions(_resolve_source_path(source_path))
    transaction_coins = [
        calculate_transaction_coins(transaction.status, transaction.amount)
        for transaction in transactions
    ]
    historical_eligible_coins = sum(transaction_coins)
    transactions_earning_coins = sum(coins > 0 for coins in transaction_coins)
    uncategorized_count = sum(
        transaction.category == "Uncategorized" for transaction in transactions
    )

    with SessionLocal.begin() as session:
        session.execute(
            text(
                "TRUNCATE TABLE redemptions, reward_wallets, transactions, rewards, users "
                "RESTART IDENTITY CASCADE"
            )
        )

        demo_user = User(name=DEMO_USER_NAME)
        session.add(demo_user)
        session.flush()

        session.execute(insert(Transaction), _transaction_mappings(transactions, demo_user.id))
        session.execute(insert(Reward), list(REWARD_CATALOG))
        # The file contains historical activity; use a controlled available balance
        # so both successful and insufficient-balance redemption demos are possible.
        session.add(
            RewardWallet(user_id=demo_user.id, balance=DEMO_INITIAL_WALLET_BALANCE)
        )
        session.flush()

        _validate_seed(
            session,
            demo_user_id=demo_user.id,
            source_record_count=report.normalized_records,
            expected_wallet_balance=DEMO_INITIAL_WALLET_BALANCE,
            expected_duplicate_count=report.duplicate_transaction_id_count,
        )

        summary = SeedSummary(
            demo_user_id=demo_user.id,
            transactions_inserted=report.normalized_records,
            rewards_inserted=len(REWARD_CATALOG),
            wallet_balance=DEMO_INITIAL_WALLET_BALANCE,
            historical_eligible_coins=historical_eligible_coins,
            transactions_earning_coins=transactions_earning_coins,
            uncategorized_transaction_count=uncategorized_count,
            report=report,
        )

    return summary


def format_seed_summary(summary: SeedSummary) -> str:
    """Format the completed seed results and parser-derived data quality report."""
    return "\n".join(
        (
            "Spendly database seeded successfully",
            "",
            "User:",
            f"Demo User (id={summary.demo_user_id})",
            "",
            "Transactions:",
            f"Source records: {summary.report.total_records}",
            f"Inserted: {summary.transactions_inserted}",
            f"Unique transaction IDs: {summary.report.unique_transaction_ids}",
            f"Duplicate IDs preserved: {summary.report.duplicate_transaction_id_count}",
            f"Uncategorized: {summary.uncategorized_transaction_count}",
            f"Negative amounts: {summary.report.negative_amount_count}",
            f"Transactions earning coins: {summary.transactions_earning_coins}",
            "",
            "Rewards:",
            f"Rewards inserted: {summary.rewards_inserted}",
            f"Historical eligible coins: {summary.historical_eligible_coins}",
            f"Demo available wallet balance: {summary.wallet_balance} coins",
            "",
            "Parser data quality:",
            format_report(summary.report),
        )
    )


def main() -> None:
    print(format_seed_summary(seed_database()))


if __name__ == "__main__":
    main()
