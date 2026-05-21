from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from server import engine
from .listings_model import listingCategory, listingOut
from .listings_model import listings as listing
from auth.dependencies import require_customer
from audit.audit import log_action

router = APIRouter()

class listingUpdate(BaseModel):
    category: Optional[listingCategory] = None
    address: Optional[str] = None
    bedrooms: Optional[int] = None
    amenities: Optional[Any] = None

@router.patch("/listings/{listing_id}", status_code=200, response_model=listingOut)
def update_listing(listing_id: int, data: listingUpdate, user_id: int = Depends(require_customer)):

    with Session(engine) as session:
        query = select(listing).where(
            listing.id == listing_id,
            listing.created_by == user_id
        )

        to_update = session.exec(query).first()

        if not to_update:
            log_action(
                session=session,
                user_id=user_id,
                action="update_listing",
                target_type="listings",
                target_id=listing_id,
                success=False,
                status_code=404,
                details={"error": "listing_not_found"}
            )
            session.commit()
            raise HTTPException(status_code=404, detail="Listing not found")
        
        old_data = {
            "category": to_update.category,
            "address": to_update.address,
            "bedrooms": to_update.bedrooms,
            "amenities": to_update.amenities
        }
        
        if data.category is not None:
            to_update.category = data.category

        if data.address is not None:
            to_update.address = data.address

        if data.bedrooms is not None:
            to_update.bedrooms = data.bedrooms

        if data.amenities is not None:
            to_update.amenities = data.amenities


        session.add(to_update)
        session.commit()
        session.refresh(to_update)

        new_data = {
            "category": to_update.category,
            "address": to_update.address,
            "bedrooms": to_update.bedrooms,
            "amenities": to_update.amenities
        }

        changes = {
            key: {"old": old_data[key], "new": new_data[key]}
            for key in old_data
            if old_data[key] != new_data[key]
        }

        log_action(
            session=session,
            user_id=user_id,
            action="update_listing",
            target_type="listings",
            target_id=listing_id,
            status_code=200,
            success=True,
            details={
                "changes": changes
            }
        )
        session.commit()

        return listingOut(
            id=to_update.id, # type: ignore
            category=to_update.category,
            address=to_update.address,
            price=float(to_update.price),
            bedrooms=to_update.bedrooms,
            amenities=to_update.amenities,
            created_at=to_update.created_at,
            updated_at=to_update.updated_at,
            created_by=to_update.created_by
        )
        