from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class RewardBalanceResponse(BaseModel):
    balance: int


class RewardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    coin_cost: int
    reward_type: str
    reward_value: Decimal | None
    active: bool


class RewardListResponse(BaseModel):
    items: list[RewardResponse]


class RewardRedemptionResponse(BaseModel):
    redemption_id: int
    reward_id: int
    reward_name: str
    coins_spent: int
    balance: int
