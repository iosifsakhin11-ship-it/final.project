from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, CHAR, text
from sqlalchemy import Integer as BIGINT


class email_verifications(SQLModel, table=True):
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

    token: str = Field(
        sa_column=Column(
            CHAR(64),
            nullable=False,
            unique=True
        )
    )

    expires_at: datetime = Field(
        sa_column=Column(
            DateTime,
            nullable=False,
            index=True
        )
    )

    used_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime,
            nullable=True
        )
    )