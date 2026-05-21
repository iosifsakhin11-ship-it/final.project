from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Annotated
from enum import Enum

from pydantic import BaseModel
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, text, Enum as SAEnum, CheckConstraint
from sqlalchemy import Integer as BIGINT, DECIMAL
from pydantic import condecimal


class BidStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    cancelled = "cancelled"

class PaymentMethod(str, Enum):
    credit_card = "credit_card"
    bank_transfer = "bank_transfer"

Amount = Annotated[
    Decimal,
    Field(gt=0, max_digits=12, decimal_places=2)
]

class CreateBid(SQLModel):
    listing_id: int
    amount: Amount
    payment_method: Optional[PaymentMethod] = None

class BidOut(BaseModel):
    id: int
    user_id: int
    listing_id: int
    message_id: Optional[int]
    amount: Decimal
    status: BidStatus
    payment_method: PaymentMethod
    created_at: datetime
    updated_at: datetime

class RespondToBid(BaseModel):
    status: BidStatus

class BidStatusOut(BaseModel):
    id: int
    status: BidStatus
    updated_at: datetime

    model_config = {"from_attributes": True}

class BidListOut(BaseModel):
    bids: list[BidOut]
    total: int

class bids(SQLModel, table=True):
    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_bid_amount"),
    )

    id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            BIGINT(),
            primary_key=True,
            autoincrement=True
        )
    )

    user_id: int = Field(
        sa_column=Column(
            BIGINT(),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False
        )
    )

    listing_id: int = Field(
        sa_column=Column(
            BIGINT(),
            ForeignKey("listings.id", ondelete="CASCADE"),
            nullable=False
        )
    )

    message_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            BIGINT(),
            ForeignKey("messages.id", ondelete="SET NULL"),
            nullable=True
        )
    )

    amount: Decimal = Field(
        sa_column=Column(
            DECIMAL(12, 2),
            nullable=False
        )
    )

    status: BidStatus = Field(
        default=BidStatus.pending,
        sa_column=Column(
            SAEnum(BidStatus),
            nullable=False,
            server_default="pending"
        )
    )

    payment_method: Optional[PaymentMethod] = Field(
        default=None,
        sa_column=Column(
            SAEnum(PaymentMethod),
            nullable=True
        )
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime,
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP")
        )
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime,
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP")
        )
    )