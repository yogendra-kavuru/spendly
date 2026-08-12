from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Redemption, Reward, RewardWallet
from app.schemas.reward import (
    RewardBalanceResponse,
    RewardListResponse,
    RewardRedemptionResponse,
    RewardResponse,
)


router = APIRouter(prefix="/api/rewards", tags=["rewards"])

DEMO_USER_ID = 1


@router.get("/balance", response_model=RewardBalanceResponse)
def get_reward_balance(db: Session = Depends(get_db)) -> RewardBalanceResponse:
    """Return the stored reward balance for the single demo user."""
    wallet = db.scalar(
        select(RewardWallet).where(RewardWallet.user_id == DEMO_USER_ID)
    )
    if wallet is None:
        raise HTTPException(status_code=404, detail="Reward wallet not found")
    return RewardBalanceResponse(balance=wallet.balance)


@router.get("", response_model=RewardListResponse)
def list_rewards(db: Session = Depends(get_db)) -> RewardListResponse:
    """Return active reward catalog entries in deterministic cost order."""
    rewards = db.scalars(
        select(Reward)
        .where(Reward.active.is_(True))
        .order_by(Reward.coin_cost.asc(), Reward.id.asc())
    ).all()
    return RewardListResponse(
        items=[RewardResponse.model_validate(reward) for reward in rewards]
    )


@router.post("/{reward_id}/redeem", response_model=RewardRedemptionResponse)
def redeem_reward(
    reward_id: int,
    db: Session = Depends(get_db),
) -> RewardRedemptionResponse:
    """Atomically redeem an active reward using the demo user's stored balance."""
    with db.begin():
        reward = db.scalar(select(Reward).where(Reward.id == reward_id))
        if reward is None:
            raise HTTPException(status_code=404, detail="Reward not found")
        if not reward.active:
            raise HTTPException(status_code=409, detail="Reward is not active")

        # Lock before checking balance so concurrent redemptions cannot overspend it.
        wallet = db.scalar(
            select(RewardWallet)
            .where(RewardWallet.user_id == DEMO_USER_ID)
            .with_for_update()
        )
        if wallet is None:
            raise HTTPException(status_code=404, detail="Reward wallet not found")
        if wallet.balance < reward.coin_cost:
            raise HTTPException(status_code=409, detail="Insufficient reward balance")

        wallet.balance -= reward.coin_cost
        redemption = Redemption(
            user_id=DEMO_USER_ID,
            reward_id=reward.id,
            coin_cost_snapshot=reward.coin_cost,
        )
        db.add(redemption)
        db.flush()

        response = RewardRedemptionResponse(
            redemption_id=redemption.id,
            reward_id=reward.id,
            reward_name=reward.name,
            coins_spent=reward.coin_cost,
            balance=wallet.balance,
        )

    return response
