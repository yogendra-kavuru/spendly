from decimal import Decimal
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.api.rewards import DEMO_USER_ID, redeem_reward
from app.database import SessionLocal, engine
from app.main import app
from app.models import Redemption, Reward, RewardWallet


client = TestClient(app)


@contextmanager
def isolated_session() -> Session:
    """Run endpoint logic inside a transaction that is always rolled back."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def test_reward_balance_returns_stored_wallet_balance() -> None:
    response = client.get("/api/rewards/balance")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload) == {"balance"}
    assert isinstance(payload["balance"], int)
    assert payload["balance"] >= 0

    with SessionLocal() as session:
        stored_balance = session.scalar(select(RewardWallet.balance).where(RewardWallet.user_id == 1))
    assert payload["balance"] == stored_balance


def test_active_reward_catalog_is_ordered_and_read_only() -> None:
    response = client.get("/api/rewards")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload) == {"items"}
    assert len(payload["items"]) == 5

    expected_fields = {
        "id",
        "name",
        "description",
        "coin_cost",
        "reward_type",
        "reward_value",
        "active",
    }
    ordering = []
    for reward in payload["items"]:
        assert set(reward) == expected_fields
        assert reward["active"] is True
        assert reward["coin_cost"] > 0
        assert Decimal(reward["reward_value"]) >= 0
        ordering.append((reward["coin_cost"], reward["id"]))
    assert ordering == sorted(ordering)

    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(Redemption)) == 0


def test_successful_redemption_is_atomic_and_snapshots_cost() -> None:
    with isolated_session() as session:
        result = redeem_reward(1, session)
        wallet = session.get(RewardWallet, DEMO_USER_ID)
        redemption = session.get(Redemption, result.redemption_id)

        assert result.reward_id == 1
        assert result.coins_spent == 500
        assert result.balance == 1000
        assert wallet is not None and wallet.balance == 1000
        assert redemption is not None
        assert redemption.coin_cost_snapshot == 500
        assert wallet.balance >= 0


def test_second_redemption_deducts_from_updated_balance() -> None:
    with isolated_session() as session:
        first = redeem_reward(1, session)
        second = redeem_reward(2, session)

        assert first.balance == 1000
        assert second.coins_spent == 900
        assert second.balance == 100
        assert session.scalar(select(func.count()).select_from(Redemption)) == 2


@pytest.mark.parametrize("reward_id", [4, 5])
def test_insufficient_balance_creates_no_redemption(reward_id: int) -> None:
    with isolated_session() as session:
        with pytest.raises(HTTPException, match="Insufficient reward balance") as error:
            redeem_reward(reward_id, session)

        assert error.value.status_code == 409
        assert session.get(RewardWallet, DEMO_USER_ID).balance == 1500
        assert session.scalar(select(func.count()).select_from(Redemption)) == 0


def test_missing_reward_creates_no_redemption() -> None:
    with isolated_session() as session:
        with pytest.raises(HTTPException, match="Reward not found") as error:
            redeem_reward(999_999, session)

        assert error.value.status_code == 404
        assert session.get(RewardWallet, DEMO_USER_ID).balance == 1500
        assert session.scalar(select(func.count()).select_from(Redemption)) == 0


def test_inactive_reward_and_missing_wallet_fail_without_writes() -> None:
    with isolated_session() as session:
        session.execute(update(Reward).where(Reward.id == 1).values(active=False))
        session.commit()
        with pytest.raises(HTTPException, match="Reward is not active") as error:
            redeem_reward(1, session)
        assert error.value.status_code == 409
        assert session.get(RewardWallet, DEMO_USER_ID).balance == 1500
        assert session.scalar(select(func.count()).select_from(Redemption)) == 0

    with isolated_session() as session:
        session.execute(delete(RewardWallet).where(RewardWallet.user_id == DEMO_USER_ID))
        session.commit()
        with pytest.raises(HTTPException, match="Reward wallet not found") as error:
            redeem_reward(1, session)
        assert error.value.status_code == 404
        assert session.scalar(select(func.count()).select_from(Redemption)) == 0
