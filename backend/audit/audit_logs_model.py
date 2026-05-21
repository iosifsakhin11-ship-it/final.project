from sqlmodel import SQLModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import Column, JSON, ForeignKey, TIMESTAMP, text
from sqlalchemy import Integer as BIGINT


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs" # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)

    user_id: Optional[int] = Field(
        sa_column=Column(
            BIGINT(),
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True
        )
    )

    action: str = Field(max_length=100, nullable=False)

    target_type: Optional[str] = Field(default=None, max_length=50)

    target_id: Optional[int] = Field(default=None)

    status_code: Optional[int] = Field(default=None)
    
    success: bool = Field(nullable=False)

    details: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON)
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )