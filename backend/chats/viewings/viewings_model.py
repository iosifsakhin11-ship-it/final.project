from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Annotated
from enum import Enum

from pydantic import BaseModel
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, text, Enum as SAEnum
from sqlalchemy import Integer as BIGINT


class ViewingStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    cancelled = "cancelled"


class CreateViewing(SQLModel):
    listing_id: int
    viewing_at: datetime


class RespondToViewing(BaseModel):
    status: ViewingStatus 


class ViewingOut(BaseModel):
    id: int
    user_id: int
    listing_id: int
    message_id: Optional[int]
    viewing_at: datetime
    status: ViewingStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ViewingStatusOut(BaseModel):
    id: int
    status: ViewingStatus
    updated_at: datetime

    model_config = {"from_attributes": True}


class ViewingListOut(BaseModel):
    viewings: list[ViewingOut]
    total: int


class viewings(SQLModel, table=True):

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

    viewing_at: datetime = Field(
        sa_column=Column(
            DateTime,
            nullable=False
        )
    )

    status: ViewingStatus = Field(
        default=ViewingStatus.pending,
        sa_column=Column(
            SAEnum(ViewingStatus),
            nullable=False,
            server_default="pending"
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