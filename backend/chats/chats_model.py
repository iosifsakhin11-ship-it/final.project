from datetime import datetime, timezone
from pydantic import BaseModel
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, text, UniqueConstraint, Text
from sqlalchemy import Integer as BIGINT


class chatOut(BaseModel):
    listing_id: int
    customer_id: int
    owner_id: int

class MessageInChat(BaseModel):
    id: int
    sender_id: int
    content:    str
    created_at: datetime

class ChatDetailOut(BaseModel):
    id: int
    listing_id: int
    customer_id: int
    owner_id: int
    created_at: datetime
    messages: list[MessageInChat]
    total_messages: int

class chats(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("listing_id", "customer_id", name="unique_listing_customer"),)

    id: int | None = Field(
        default=None,
        sa_column=Column(
            BIGINT(),
            primary_key=True,
            autoincrement=True
        )
    )
    
    listing_id: int = Field(
        sa_column=Column(
            BIGINT(),
            ForeignKey("listings.id", ondelete="CASCADE"),
            nullable=False
        )
    )

    customer_id: int = Field(
        sa_column=Column(
            BIGINT(),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False
        )
    )

    owner_id: int = Field(
        sa_column=Column(
            BIGINT(),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False
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

class messageCreate(BaseModel):
    listing_id: int
    content: str

class messageOut(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    content: str
    created_at: datetime

class MessagePayload(BaseModel):
    listing_id: int
    content: str

class messages(SQLModel, table=True):
    id: int | None = Field(
        default=None,
        sa_column=Column(
            BIGINT(),
            primary_key=True,
            autoincrement=True
        )
    )

    chat_id: int = Field(
        sa_column=Column(
            BIGINT(),
            ForeignKey("chats.id", ondelete="CASCADE"),
            nullable=False
        )
    )

    sender_id: int = Field(
        sa_column=Column(
            BIGINT(),
            ForeignKey("users.id"),
            nullable=False
        )
    )

    content: str = Field(
        sa_column=Column(
            Text,
            nullable=False
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
