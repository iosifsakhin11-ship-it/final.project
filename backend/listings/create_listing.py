from fastapi import APIRouter, HTTPException, Depends
from pydantic import AnyHttpUrl
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session
from auth.dependencies import require_customer
from server import engine
from .listings_model import listingCreate, listingOut, ListingPhoto
from .listings_model import listings as listing
from audit.audit import log_action
from urllib.parse import urlparse
from subscriptions.subscriptions import notify_subscribers


router = APIRouter()


@router.post("/listings", status_code=201, response_model=listingOut)
def create_listing(data: listingCreate, user_id: int = Depends(require_customer)):

    with Session(engine) as session:

        new_listing = listing(
            category=data.category,
            address=data.address,
            price=data.price,
            bedrooms=data.bedrooms,
            amenities=data.amenities,
            created_by=user_id
        )
        session.add(new_listing)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()

            log_action(
                session=session,
                user_id=user_id,
                action="create_listing",
                target_type="listings",
                success=False,
                status_code=400,
                details={"error": "IntegrityError"}
            )
            session.commit()

            raise HTTPException(status_code=400, detail="error with input data")
        session.refresh(new_listing)

        if data.photos:
            for index, url in enumerate(data.photos):
                photo = ListingPhoto(
                    listing_id=new_listing.id, # type: ignore
                    url=str(url),
                    sort_order=index,
                    is_primary=(index == 0)
                )
                session.add(photo) # type: ignore

        log_action(
            session=session,
            user_id=user_id,
            action="create_listing",
            target_type="listings",
            target_id=new_listing.id,
            success=True,
            status_code=201,
            details={
                "category": data.category,
                "price": data.price
            }
        )
        session.commit()

        notify_subscribers(session, new_listing)

        return listingOut(
            id=new_listing.id, # type: ignore
            category=new_listing.category,
            status=new_listing.status, # type: ignore
            address=new_listing.address,
            price=float(new_listing.price),
            bedrooms=new_listing.bedrooms,
            amenities=new_listing.amenities,
            created_at=new_listing.created_at,
            updated_at=new_listing.updated_at,
            created_by=new_listing.created_by
        )
