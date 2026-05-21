from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, CHAR
from sqlalchemy import Integer as BIGINT


class two_factor_tokens(SQLModel, table=True):
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

    otp: str = Field(
        sa_column=Column(
            CHAR(6),
            nullable=False
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