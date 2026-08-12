from decimal import Decimal

import pytest

from app.data.seed import DEMO_INITIAL_WALLET_BALANCE, calculate_transaction_coins


def test_demo_initial_wallet_balance_is_controlled() -> None:
    assert DEMO_INITIAL_WALLET_BALANCE == 1500


@pytest.mark.parametrize(
    ("status", "amount", "expected_coins"),
    [
        ("SUCCESS", Decimal("99.99"), 0),
        ("SUCCESS", Decimal("100"), 1),
        ("SUCCESS", Decimal("199.99"), 1),
        ("SUCCESS", Decimal("500"), 5),
        ("SUCCESS", Decimal("10000"), 100),
        ("SUCCESS", Decimal("25000"), 100),
        ("FAILED", Decimal("500"), 0),
        ("PENDING", Decimal("500"), 0),
        ("SUCCESS", Decimal("-500"), 0),
        ("SUCCESS", Decimal("0"), 0),
    ],
)
def test_calculate_transaction_coins(
    status: str, amount: Decimal, expected_coins: int
) -> None:
    assert calculate_transaction_coins(status, amount) == expected_coins
