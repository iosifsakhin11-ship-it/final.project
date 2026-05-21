from sqlmodel import SQLModel, Field
from pydantic import BaseModel
from sqlalchemy import ForeignKey, DateTime, CHAR, text, Column, Enum as SAEnum, Boolean
from datetime import datetime, timezone
from sqlalchemy import Integer as BIGINT
from typing import Optional
from enum import Enum

class UserCreateRequest(BaseModel):
    username: str
    email:    str
    password: str

class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    email:    Optional[str] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password:     str

class userType(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUPERVISOR = "supervisor"

class users(SQLModel, table=True):
    id: int | None = Field(
        default=None,
        sa_column=Column(
            BIGINT(),
            primary_key=True,
            autoincrement=True
        )
    )
        
    username: str = Field(index=True, unique=True, nullable=False, max_length=255)
    email: str = Field(unique=True, nullable=False, max_length=255)
    password_hash: str = Field(nullable=False, max_length=255)

    type: str = Field(
        default="user",
        sa_column=Column(
            SAEnum(
                "user",
                "admin",
                "supervisor",
                name="user_type"
            ),
            nullable=False,
            server_default="user"
        )
    )

    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime,
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP")
        )
    )

    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime,
            nullable=True,
            server_default=text("CURRENT_TIMESTAMP"),
            onupdate=text("CURRENT_TIMESTAMP")
        )
    )

    is_verified: bool = Field(
        default=False,
        sa_column=Column(
            Boolean,
            nullable=False,
            server_default=text("0")
        )
    )

    is_banned: bool = Field(
        default=False,
        sa_column=Column(
            Boolean,
            nullable=False,
            server_default=text("0")
        )
    )


class userRead(BaseModel):
    id: int
    username: str
    email: str
    type: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    is_verified: bool

class LoginResponse(BaseModel):
    message: str
    token: str
    user: userRead

class LogoutResponse(BaseModel):
    message: str

class user_sessions(SQLModel, table=True):
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
            index=True,
        )
    )

    token: str = Field(
        sa_column=Column(
            CHAR(64),
            nullable=False,
            unique=True
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

    last_seen: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime,
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            onupdate=text("CURRENT_TIMESTAMP"),
        )
    )

    expires_at: datetime = Field(
        sa_column=Column(
            DateTime,
            nullable=False,
            index=True
        )
    )

    revoked_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime,
            nullable=True
        )
    )

class OTPRequest(BaseModel):
    email:    str
    password: str

class OTPVerify(BaseModel):
    email: str
    otp:   str

class OTPResponse(BaseModel):
    message: str