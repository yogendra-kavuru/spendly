from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_id: str
    transaction_at: datetime
    merchant: str
    category: str
    amount: Decimal
    currency: str
    status: str
    payment_method: str


class PaginatedTransactions(BaseModel):
    items: list[TransactionResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


class TransactionMetadataResponse(BaseModel):
    categories: list[str]
    statuses: list[str]
    payment_methods: list[str]
