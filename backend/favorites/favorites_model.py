from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, ForeignKey, text
from sqlalchemy import Integer as BIGINT
from sqlmodel import Field, SQLModel
from typing import List

class FavoriteOut(BaseModel):
    id: int
    listing_id: int
    user_id: int

class FavoriteListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[FavoriteOut]
class user_favorites(SQLModel, table=True):
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
            ForeignKey("users.id"),
            nullable=False,
            index=True
        )
    )

    listing_id: int = Field(
                sa_column=Column(
            BIGINT(),
            ForeignKey("listings.id"),
            nullable=False,
            index=True
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