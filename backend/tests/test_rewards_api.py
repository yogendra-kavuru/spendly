from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database import SessionLocal
from app.main import app
from app.models import Redemption, RewardWallet


client = TestClient(app)


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
