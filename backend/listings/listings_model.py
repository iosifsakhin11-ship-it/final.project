from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Any

from pydantic import BaseModel, AnyHttpUrl
from sqlalchemy import DECIMAL, Boolean, Integer, Column, DateTime, Enum as SAEnum, ForeignKey, Text, text, JSON
from sqlalchemy import Integer as BIGINT, SmallInteger as TINYINT
from sqlmodel import Field, SQLModel

class listingCategory(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    RENTAL = "rental"
    OTHER = "other"

class listingStatus(str, Enum):
    ACTIVE = "active"
    UNLISTED = "unlisted"
    SOLD = "sold"

class ListingPhotoOut(BaseModel):
    url: AnyHttpUrl
    sort_order: int
    is_primary: bool

class listingCreate(BaseModel):
    category: listingCategory
    address: str
    price: float
    bedrooms: Optional[int] = None
    amenities: Optional[Any] = None
    photos: list[AnyHttpUrl] | None = None

class listingOut(BaseModel):
    id: int
    category: str
    address: str
    price: float
    status: listingStatus
    bedrooms: Optional[int] = None
    amenities: Optional[Any] = None
    photos: list[ListingPhotoOut] = []
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: int

class listingListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[listingOut]

class listings(SQLModel, table=True):
    id: int | None = Field(
        default=None,
        sa_column=Column(
            BIGINT(),
            primary_key=True,
            autoincrement=True
        )
    )

    category: str = Field(
        sa_column= Column(
            SAEnum(
                "residential",
                "commercial",
                "rental",
                "other",
                name="listing_category"
                ),
            nullable=False
        )
    )


    status: str = Field(
        default="active",
        sa_column=Column(
            SAEnum(
                "active",
                "unlisted",
                "sold",
                name="listing_status"
            ),
            nullable=False,
            server_default="active"
        )
    )

    address: str = Field(
        nullable=False,
        max_length=255
    )

    price: float = Field(
        sa_column=Column(
            DECIMAL(12,2),
            nullable=False
        )
    )

    bedrooms: int | None = Field(
        default=None,
        sa_column=Column(
            TINYINT(),
            nullable=True
        )
    )

    amenities: Any | None = Field(
        default=None,
        sa_column=Column(
            JSON,
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
    
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime,
            nullable=True,
            server_default=text("CURRENT_TIMESTAMP"),
            onupdate=text("CURRENT_TIMESTAMP")
        )
    )

    created_by: int = Field(
        sa_column=Column(
            BIGINT(),
            ForeignKey("users.id"),
            nullable=False,
            index=True,
        )
    )

class ListingPhotoCreate(BaseModel):
    listing_id: int
    url: str
    is_primary: bool = False

class ListingPhoto(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    listing_id: int = Field(foreign_key="listings.id", index=True)

    url: str

    is_primary: bool = Field(default=False)

    sort_order: int = Field(default=0)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))