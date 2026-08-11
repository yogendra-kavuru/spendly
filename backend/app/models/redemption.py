from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Redemption(Base):
    __tablename__ = "redemptions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    reward_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("rewards.id"), nullable=False
    )
    coin_cost_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="redemptions")
    reward: Mapped["Reward"] = relationship(back_populates="redemptions")
