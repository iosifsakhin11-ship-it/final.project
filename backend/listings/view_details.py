from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from typing import Optional
from decimal import Decimal

from .listings_model import listings, listingOut, ListingPhotoOut, ListingPhoto
from server import engine
from pydantic import BaseModel

router = APIRouter()

@router.get("/listings/{listing_id}", response_model=listingOut, status_code=200)
def get_listing_details(listing_id: int):
    with Session(engine) as session:
        listing_row = session.exec(select(listings).where(listings.id == listing_id)).first()
        if not listing_row:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        photos = session.exec(
            select(ListingPhoto)
            .where(ListingPhoto.listing_id == listing_id)
        ).all()

        return listingOut(
            id=listing_row.id, # type: ignore
            category=listing_row.category,
            status=listing_row.status,
            address=listing_row.address,
            price=float(listing_row.price),
            bedrooms=listing_row.bedrooms,
            amenities=listing_row.amenities,
            created_at=listing_row.created_at,
            updated_at=listing_row.updated_at,
            created_by=listing_row.created_by,

            photos=[
                ListingPhotoOut(
                    url=p.url, # type: ignore
                    sort_order=p.sort_order,
                    is_primary=p.is_primary
                )
                for p in photos
            ]
        )
