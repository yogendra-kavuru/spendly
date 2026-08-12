from decimal import Decimal

from pydantic import BaseModel


class CategorySpendItem(BaseModel):
    category: str
    amount: Decimal
    transaction_count: int


class CategorySpendResponse(BaseModel):
    month: str
    items: list[CategorySpendItem]
    total_spend: Decimal
