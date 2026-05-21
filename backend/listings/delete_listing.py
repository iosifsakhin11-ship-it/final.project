from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from auth.dependencies import require_customer
from server import engine
from .listings_model import listings as listing
from audit.audit import log_action
from pydantic import BaseModel

router = APIRouter()

class ListingDeleteOut(BaseModel):
    deleted: bool
    listing_id: int

@router.delete("/listings/{listing_id}", response_model=ListingDeleteOut, status_code=200)
def delete_listing(listing_id: int, user_id : int = Depends(require_customer)):

    with Session(engine) as session:

        statment = select(listing).where(
            listing.id == listing_id,
            listing.created_by == user_id
            )
        to_delete = session.exec(statment).first()

        if not to_delete:

            log_action(
                session=session,
                user_id = user_id,
                action="delete_listing",
                target_type="listings",
                target_id=listing_id,
                success=False,
                status_code=404,
                details={"error": "IntegrityError"}
            )
            session.commit()

            raise HTTPException(status_code=404, detail="Listing not found")
        
        info = {
            "id": to_delete.id,
            "category": to_delete.category,
            "address": to_delete.address,
            "price": float(to_delete.price)
        }

        session.delete(to_delete)

        try:
            session.commit()
        except Exception:
            session.rollback()

            log_action(
                session=session,
                user_id=user_id,
                action="delete_listing",
                target_type="listings",
                target_id=listing_id,
                success=False,
                status_code=500,
                details={"error": "delete_failed"}
            )
            session.commit()

            raise HTTPException(status_code=500, detail="Delete failed")
               
        log_action(
            session=session,
            user_id=user_id,
            action="delete_listing",
            target_type="listings",
            target_id=listing_id,
            success=True,
            status_code=200,
            details={
                "deleted_object": info
            }
        )
        session.commit()


        return {
            "deleted": True,
            "listing_id": listing_id
        }
