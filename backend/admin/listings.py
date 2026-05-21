from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session, select
from server import engine
from listings.listings_model import listings as listing, listingOut, listingStatus
from .dependencies import require_admin
from audit.audit import log_action
from .admins_models import AdminListingBrowse,AdminListingUpdate, AdminListingListResponse
from chats.send_message import message_service
from chats.bids.bids_model import bids, BidStatus
from chats.chats_model import MessagePayload
from chats.viewings.viewings_model import viewings, ViewingStatus

router = APIRouter()


def admin_delete_listing_service(session: Session, listing_id: int, admin_id: int):

    target_listing = session.exec(
        select(listing).where(listing.id == listing_id)
    ).first()

    if not target_listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    info = {
        "id": target_listing.id,
        "address": target_listing.address,
        "category": target_listing.category,
        "price": float(target_listing.price),
        "owner": target_listing.created_by
    }

    session.delete(target_listing)
    session.commit()

    log_action(
        session=session,
        user_id=admin_id,
        action="admin_delete_listing",
        target_type="listings",
        target_id=listing_id,
        success=True,
        status_code=200,
        details={"deleted_listing": info}
    )
    session.commit()

    return {
        "deleted": True,
        "listing_id": listing_id
    }


@router.delete("/admin/listings/{listing_id}", status_code=200)
def admin_delete_listing(listing_id: int, admin_id: int = Depends(require_admin)):
    with Session(engine) as session:
        try:
            return admin_delete_listing_service(session, listing_id, admin_id)
        except HTTPException as e:
            session.rollback()
            log_action(
                session=session,
                user_id=admin_id,
                action="admin_delete_listing",
                target_type="listings",
                target_id=listing_id,
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail)}
            )
            session.commit()
            raise

def admin_update_listing_service(session: Session, listing_id: int, data: AdminListingUpdate, admin_id: int):

    target_listing = session.exec(
        select(listing).where(listing.id == listing_id)
    ).first()

    if not target_listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    old_data = {
        "category": target_listing.category,
        "address": target_listing.address,
        "price": float(target_listing.price),
        "bedrooms": target_listing.bedrooms,
        "amenities": target_listing.amenities,
        "status": target_listing.status,
    }

    if data.category is not None:
        target_listing.category = data.category

    if data.address is not None:
        target_listing.address = data.address

    if data.price is not None:
        target_listing.price = data.price # type: ignore

    if data.bedrooms is not None:
        target_listing.bedrooms = data.bedrooms

    if data.amenities is not None:
        target_listing.amenities = data.amenities

    if data.status is not None:
        target_listing.status = data.status

        if data.status == listingStatus.SOLD:
            pending_bids = session.exec(
                select(bids).where(
                    bids.listing_id == listing_id,
                    bids.status == BidStatus.pending
                )
            ).all()

            for bid in pending_bids:
                bid.status = BidStatus.rejected
                session.add(bid)
                rejection_payload = MessagePayload(
                    listing_id=listing_id,
                    content=f"Your bid of £{bid.amount:.2f} has been rejected as the listing has been marked as sold."
                )
                message_service(session, rejection_payload, bid.user_id)

            pending_viewings = session.exec(
                select(viewings).where(
                    viewings.listing_id == listing_id,
                    viewings.status == ViewingStatus.pending
                )
            ).all()

            for viewing in pending_viewings:
                viewing.status = ViewingStatus.rejected
                session.add(viewing)
                viewing_payload = MessagePayload(
                    listing_id=listing_id,
                    content=f"Your viewing request for {viewing.viewing_at.strftime('%A %d %B %Y at %H:%M')} has been cancelled as the listing has been marked as sold."
                )
                message_service(session, viewing_payload, viewing.user_id)

    session.add(target_listing)
    session.commit()
    session.refresh(target_listing)

    new_data = {
        "category": target_listing.category,
        "address": target_listing.address,
        "price": float(target_listing.price),
        "bedrooms": target_listing.bedrooms,
        "amenities": target_listing.amenities,
        "status": target_listing.status,
    }

    changes = {
        key: {"old": old_data[key], "new": new_data[key]}
        for key in old_data
        if old_data[key] != new_data[key]
    }

    log_action(
        session=session,
        user_id=admin_id,
        action="admin_update_listing",
        target_type="listings",
        target_id=listing_id,
        success=True,
        status_code=200,
        details={
            "changes": changes,
            "listing_id": listing_id,
            "owner": target_listing.created_by
        }
    )
    session.commit()

    return {
        "id": target_listing.id,
        "category": target_listing.category,
        "address": target_listing.address,
        "price": float(target_listing.price),
        "status": target_listing.status,
        "bedrooms": target_listing.bedrooms,
        "amenities": target_listing.amenities,
        "created_at": target_listing.created_at,
        "updated_at": target_listing.updated_at,
        "created_by": target_listing.created_by,
        "photos": []
    }


@router.patch("/admin/listings/{listing_id}", response_model=listingOut, status_code=200)
def admin_update_listing(listing_id: int, data: AdminListingUpdate, admin_id: int = Depends(require_admin)):
    with Session(engine) as session:
        try:
            return admin_update_listing_service(session, listing_id, data, admin_id)
        except HTTPException as e:
            session.rollback()
            log_action(
                session=session,
                user_id=admin_id,
                action="admin_update_listing",
                target_type="listings",
                target_id=listing_id,
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail), "listing_id": listing_id}
            )
            session.commit()
            raise

def admin_get_listings_service(session: Session, filters: AdminListingBrowse, limit: int, offset: int):

    base_query = select(listing)

    if filters.category is not None:
        base_query = base_query.where(listing.category == filters.category)

    if filters.status is not None:
        base_query = base_query.where(listing.status == filters.status)

    if filters.min_price is not None:
        base_query = base_query.where(listing.price >= filters.min_price)

    if filters.max_price is not None:
        base_query = base_query.where(listing.price <= filters.max_price)

    if filters.bedrooms is not None:
        base_query = base_query.where(listing.bedrooms == filters.bedrooms)

    if filters.created_by is not None:
        base_query = base_query.where(listing.created_by == filters.created_by)

    total = session.exec(
        select(func.count()).select_from(base_query.subquery())
    ).one()

    results = session.exec(
        base_query.offset(offset).limit(limit)
    ).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": r.id,
                "category": r.category,
                "address": r.address,
                "price": float(r.price),
                "status": r.status,
                "bedrooms": r.bedrooms,
                "amenities": r.amenities,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
                "created_by": r.created_by,
                "photos": []
            }
            for r in results
        ]
    }


@router.get("/admin/listings", response_model=AdminListingListResponse, status_code=200)
def admin_get_listings(
    filters: AdminListingBrowse = Depends(),
    limit: int = 20,
    offset: int = 0,
    admin_id: int = Depends(require_admin)
):
    with Session(engine) as session:
        try:
            return admin_get_listings_service(session, filters, limit, offset)
        except HTTPException as e:
            session.rollback()
            log_action(
                session=session,
                user_id=admin_id,
                action="admin_get_listings",
                target_type="listings",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail)}
            )
            session.commit()
            raise