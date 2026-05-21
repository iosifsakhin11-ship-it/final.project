from pydantic import BaseModel
from typing import Optional

class ListingActivityOut(BaseModel):
    listing_id: int
    address: str
    messages: int
    bids: int
    viewings: int
    total_activity: int

class MonthlyTrendOut(BaseModel):
    month: str
    messages: int
    bids: int
    viewings: int

class InquiryReportOut(BaseModel):
    from_month: str
    to_month: str
    summary: dict
    most_inquired_listings: list[ListingActivityOut]
    monthly_trends: list[MonthlyTrendOut]

class ListingFavouriteStatsOut(BaseModel):
    listing_id: int
    address: str
    category: str
    price: float
    total_favourites: int

class MonthlyFavouriteTrendOut(BaseModel):
    month: str
    total_favourites: int

class SavedListingsReportOut(BaseModel):
    from_month: str
    to_month: str
    summary: dict
    most_saved_listings: list[ListingFavouriteStatsOut]
    monthly_trends: list[MonthlyFavouriteTrendOut]

class FilterTrendOut(BaseModel):
    filter_value: str
    count: int

class SearchTrendsReportOut(BaseModel):
    from_month: str
    to_month: str
    summary: dict
    popular_categories: list[FilterTrendOut]
    popular_types: list[FilterTrendOut]
    popular_bedrooms: list[FilterTrendOut]
    price_ranges: dict
    monthly_trends: list[dict]