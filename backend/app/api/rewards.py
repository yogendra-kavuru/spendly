from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Reward, RewardWallet
from app.schemas.reward import RewardBalanceResponse, RewardListResponse, RewardResponse


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
