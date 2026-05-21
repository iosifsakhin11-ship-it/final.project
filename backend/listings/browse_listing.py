from typing import Optional, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select, func, String
from server import engine
from .listings_model import listingCategory, listingOut, listingListResponse
from .listings_model import listings as listing
from audit.audit import log_action
from auth.dependencies import get_current_user_id

router = APIRouter()

class listingBrowse(BaseModel):
    listing_id: Optional[int] = None
    category: Optional[listingCategory] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    bedrooms: Optional[int] = None
    location: Optional[str] = None        # FR-6: text search on address
    amenities: Optional[str] = None       # FR-6: comma-separated, e.g. "pool,garden"

@router.get("/listings", status_code=200, response_model=listingListResponse)
def browse_listings(
    filters: listingBrowse = Depends(),
    limit: int = 20,
    offset: int = 0,
    token: Optional[str] = None
):
    with Session(engine) as session:
        
        base_query = select(listing).where(listing.status == "active")

        if filters.listing_id is not None:
            base_query = base_query.where(listing.id == filters.listing_id)

        if filters.category is not None:
            base_query = base_query.where(listing.category == filters.category)

        if filters.min_price is not None:
            base_query = base_query.where(listing.price >= filters.min_price)

        if filters.max_price is not None:
            base_query = base_query.where(listing.price <= filters.max_price)

        if filters.bedrooms is not None:
            base_query = base_query.where(listing.bedrooms == filters.bedrooms)

        # FR-6: Location filter — case-insensitive substring match on address
        if filters.location is not None and filters.location.strip():
            base_query = base_query.where(
                listing.address.ilike(f"%{filters.location.strip()}%")
            )

        # FR-6: Amenities filter — checks JSON array contains each requested amenity
        if filters.amenities is not None and filters.amenities.strip():
            requested = [a.strip().lower() for a in filters.amenities.split(",") if a.strip()]
            for amenity in requested:
                base_query = base_query.where(
                    func.lower(func.cast(listing.amenities, String)).contains(amenity)
                )

        count_query = select(func.count()).select_from(base_query.subquery())
        result = session.execute(count_query)
        total = result.scalar_one()

        query = base_query.offset(offset).limit(limit)
        results = session.exec(query).all()


        items = [
            listingOut(
                id=r.id, # type: ignore
                category=r.category,
                status=r.status,
                address=r.address,
                price=float(r.price),
                bedrooms=r.bedrooms,
                amenities=r.amenities,
                created_at=r.created_at,
                updated_at=r.updated_at,
                created_by=r.created_by
            )
            for r in results
        ]

        active_filters = {k: v for k, v in {
            "category": filters.category,
            "min_price": filters.min_price,
            "max_price": filters.max_price,
            "bedrooms": filters.bedrooms,
            "location": filters.location,
            "amenities": filters.amenities,
        }.items() if v is not None}

        if active_filters: 
            log_action(
                session=session,
                user_id=None,
                action="search_listings",
                target_type="listings",
                success=True,
                status_code=200,
                details=active_filters
            )
            session.commit()

        return listingListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=items
        )