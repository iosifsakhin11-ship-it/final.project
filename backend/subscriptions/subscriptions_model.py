from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, Enum as SAEnum, text
from sqlalchemy import Integer as BIGINT, DECIMAL, SmallInteger as TINYINT
from pydantic import BaseModel
from listings.listings_model import listingCategory


class listing_subscriptions(SQLModel, table=True):
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

    favourite_id: int | None = Field(
        default=None,
        sa_column=Column(
            BIGINT(),
            ForeignKey("user_favorites.id", ondelete="SET NULL"),
            nullable=True
        )
    )

    category: str | None = Field(
        default=None,
        sa_column=Column(
            SAEnum("residential", "commercial", name="sub_category"),
            nullable=True
        )
    )

    min_price: Decimal | None = Field(
        default=None,
        sa_column=Column(DECIMAL(12, 2), nullable=True)
    )

    max_price: Decimal | None = Field(
        default=None,
        sa_column=Column(DECIMAL(12, 2), nullable=True)
    )

    bedrooms: int | None = Field(
        default=None,
        sa_column=Column(TINYINT(), nullable=True)
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime,
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP")
        )
    )


class SubscriptionOut(BaseModel):
    id: int
    user_id: int
    favourite_id: Optional[int]
    category:Optional[str]
    min_price: Optional[Decimal]
    max_price: Optional[Decimal]
    bedrooms: Optional[int]
    created_at: datetime


class SubscriptionListOut(BaseModel):
    subscriptions: list[SubscriptionOut]
    total: int


class CreateSubscription(BaseModel):
    favourite_id: Optional[int]    = None
    category: Optional[listingCategory] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    bedrooms: Optional[int]     = None