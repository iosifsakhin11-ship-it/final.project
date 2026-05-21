from pydantic import BaseModel
from typing import Optional, Any
from auth.user_model import users
from datetime import datetime
from decimal import Decimal
from listings.listings_model import listingOut, listingCategory, listingStatus

class AdminUserUpdate(BaseModel):
    type: Optional[str] = None
    is_banned: Optional[bool] = None
    is_verified: Optional[bool] = None

class AdminUserRead(BaseModel):
    id: int
    username: str
    email: str
    type: str
    is_verified: bool
    is_banned: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

class AdminUserListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[AdminUserRead]

class AdminListingListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[listingOut]


class AdminListingBrowse(BaseModel):
    category: Optional[listingCategory] = None
    status: Optional[listingStatus] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    bedrooms: Optional[int] = None
    created_by: Optional[int] = None 

class AdminListingUpdate(BaseModel):
    category: Optional[listingCategory] = None
    address: Optional[str] = None
    price: Optional[Decimal] = None
    bedrooms: Optional[int] = None
    amenities: Optional[Any] = None
    status: Optional[listingStatus] = None 