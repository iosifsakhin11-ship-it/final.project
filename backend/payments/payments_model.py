from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from enum import Enum

from pydantic import BaseModel
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, text, Enum as SAEnum, CHAR
from sqlalchemy import Integer as BIGINT, DECIMAL


class PaymentStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"


class PaymentMethod(str, Enum):
    credit_card = "credit_card"
    bank_transfer = "bank_transfer"


class payment_records(SQLModel, table=True):
    id: int | None = Field(
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
            nullable=False,
            index=True
        )
    )

    bid_id: int | None = Field(
        default=None,
        sa_column=Column(
            BIGINT(),
            ForeignKey("bids.id", ondelete="SET NULL"),
            nullable=True,
            index=True
        )
    )

    amount: Decimal = Field(
        sa_column=Column(
            DECIMAL(12, 2),
            nullable=False
        )
    )

    payment_method: str = Field(
        sa_column=Column(
            SAEnum(PaymentMethod),
            nullable=False
        )
    )

    status: str = Field(
        default="pending",
        sa_column=Column(
            SAEnum(PaymentStatus),
            nullable=False,
            server_default="pending"
        )
    )

    reference: str | None = Field(
        default=None,
        sa_column=Column(
            CHAR(64),
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


class PaymentOut(BaseModel):
    id: int
    user_id: int
    bid_id: Optional[int]
    amount: Decimal
    payment_method: PaymentMethod
    status: PaymentStatus
    reference: Optional[str]
    created_at: datetime
    updated_at: datetime


class PaymentListOut(BaseModel):
    payments: list[PaymentOut]
    total: int


class AdminPaymentStatusUpdate(BaseModel):
    status: PaymentStatus
    reference: Optional[str] = None