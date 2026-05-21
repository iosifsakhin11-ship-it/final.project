from listings.listings_model import listings as listing, listingStatus
from .viewings_model import viewings, ViewingStatus, CreateViewing, ViewingOut, ViewingStatusOut, ViewingListOut, RespondToViewing
from ..chats_model import MessagePayload
from sqlmodel import Session, select
from audit.audit import log_action
from fastapi import HTTPException, APIRouter, Depends
from chats.send_message import message_service
from server import engine
from auth.dependencies import get_current_user_id, require_customer
from datetime import datetime, timezone
from auth.email_service import (
    send_viewing_confirmation_email,
    send_viewing_accepted_email,
    send_viewing_rejected_email,
    send_viewing_cancelled_email
)
from auth.user_model import users

router = APIRouter()


def create_viewing_service(session: Session, payload: CreateViewing, user_id: int):

    existing_listing = session.exec(
        select(listing).where(listing.id == payload.listing_id)
    ).first()

    if not existing_listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if existing_listing.created_by == user_id:
        log_action(
            session=session,
            user_id=user_id,
            action="create_viewing",
            target_type="viewings",
            success=False,
            status_code=409,
            details={"reason": "attempted viewing on own listing", "listing_id": payload.listing_id}
        )
        session.commit()
        raise HTTPException(status_code=409, detail="Cannot request a viewing on your own listing")

    if existing_listing.status != listingStatus.ACTIVE:
        raise HTTPException(
            status_code=409,
            detail=f"This listing is no longer available"
        )

    existing_viewing = session.exec(
        select(viewings).where(
            viewings.listing_id == payload.listing_id,
            viewings.user_id == user_id,
            viewings.status == ViewingStatus.pending
        )
    ).first()

    if existing_viewing:
        log_action(
            session=session,
            user_id=user_id,
            action="create_viewing",
            target_type="viewings",
            success=False,
            status_code=409,
            details={"reason": "duplicate pending viewing", "listing_id": payload.listing_id}
        )
        session.commit()
        raise HTTPException(status_code=409, detail="You already have a pending viewing for this listing")

    new_viewing = viewings(
        user_id=user_id,
        listing_id=payload.listing_id,
        viewing_at=payload.viewing_at,
        status=ViewingStatus.pending
    )
    session.add(new_viewing)
    session.flush()

    viewing_message_payload = MessagePayload(
        listing_id=payload.listing_id,
        content=f"I'd like to request a viewing on {payload.viewing_at.strftime('%A %d %B %Y at %H:%M')}."
    )

    sent_message = message_service(session, viewing_message_payload, user_id)

    new_viewing.message_id = sent_message["id"]
    session.add(new_viewing)
    session.commit()
    session.refresh(new_viewing)

    user_obj = session.exec(select(users).where(users.id == user_id)).first()
    if user_obj:
        send_viewing_confirmation_email(
            email=user_obj.email,
            address=existing_listing.address,
            viewing_at=payload.viewing_at.strftime('%A %d %B %Y at %H:%M'),
            viewing_id=new_viewing.id  # type: ignore
        )

    log_action(
        session=session,
        user_id=user_id,
        action="create_viewing",
        target_type="viewings",
        target_id=new_viewing.id,
        success=True,
        status_code=201,
        details={"listing_id": payload.listing_id, "viewing_at": str(payload.viewing_at)}
    )

    session.commit()
    session.refresh(new_viewing)

    return {
        "id": new_viewing.id,
        "user_id": new_viewing.user_id,
        "listing_id": new_viewing.listing_id,
        "message_id": new_viewing.message_id,
        "viewing_at": new_viewing.viewing_at,
        "status": new_viewing.status,
        "created_at": new_viewing.created_at,
        "updated_at": new_viewing.updated_at,
    }


@router.post("/viewings", response_model=ViewingOut, status_code=201)
def create_viewing(payload: CreateViewing, user_id: int = Depends(require_customer)):
    with Session(engine) as session:
        try:
            return create_viewing_service(session, payload, user_id)
        except HTTPException as e:
            session.rollback()
            log_action(
                session=session,
                user_id=user_id,
                action="create_viewing",
                target_type="viewings",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail)}
            )
            session.commit()
            raise


def respond_to_viewing_service(session: Session, viewing_id: int, payload: RespondToViewing, user_id: int):

    if payload.status not in (ViewingStatus.accepted, ViewingStatus.rejected):
        raise HTTPException(status_code=422, detail="Response must be accepted or rejected")

    existing_viewing = session.exec(
        select(viewings).where(viewings.id == viewing_id)
    ).first()

    if not existing_viewing:
        raise HTTPException(status_code=404, detail="Viewing not found")

    existing_listing = session.exec(
        select(listing).where(listing.id == existing_viewing.listing_id)
    ).first()

    if existing_listing.created_by != user_id:  # type: ignore
        raise HTTPException(status_code=403, detail="Only the listing owner can respond to a viewing request")

    if existing_viewing.status != ViewingStatus.pending:
        status_messages = {
            ViewingStatus.accepted: "This viewing has already been confirmed",
            ViewingStatus.rejected: "This viewing has already been rejected",
            ViewingStatus.cancelled: "This viewing has been cancelled by the requester",
        }
        raise HTTPException(
            status_code=409,
            detail=status_messages.get(existing_viewing.status, "This viewing cannot be responded to")
        )

    existing_viewing.status = payload.status
    session.add(existing_viewing)
    session.commit()
    session.refresh(existing_viewing)

    response_word = "confirmed" if payload.status == ViewingStatus.accepted else "rejected"
    notification_payload = MessagePayload(
        listing_id=existing_viewing.listing_id,
        content=f"Your viewing request for {existing_viewing.viewing_at.strftime('%A %d %B %Y at %H:%M')} has been {response_word}."
    )
    message_service(session, notification_payload, existing_viewing.user_id)

    viewer = session.exec(
        select(users).where(users.id == existing_viewing.user_id)
    ).first()

    if viewer:
        viewing_at_str = existing_viewing.viewing_at.strftime('%A %d %B %Y at %H:%M')
        if payload.status == ViewingStatus.accepted:
            send_viewing_accepted_email(
                email=viewer.email,
                address=existing_listing.address, # type: ignore
                viewing_at=viewing_at_str,
                viewing_id=existing_viewing.id  # type: ignore
            )
        else:
            send_viewing_rejected_email(
                email=viewer.email,
                address=existing_listing.address, # type: ignore
                viewing_at=viewing_at_str,
                viewing_id=existing_viewing.id  # type: ignore
            )

    log_action(
        session=session,
        user_id=user_id,
        action="respond_to_viewing",
        target_type="viewings",
        target_id=existing_viewing.id,
        success=True,
        status_code=200,
        details={"new_status": payload.status.value, "viewing_id": viewing_id}
    )
    session.commit()
    session.refresh(existing_viewing)

    return {
        "id": existing_viewing.id,
        "status": existing_viewing.status,
        "updated_at": existing_viewing.updated_at,
    }


def cancel_viewing_service(session: Session, viewing_id: int, user_id: int):

    existing_viewing = session.exec(
        select(viewings).where(viewings.id == viewing_id)
    ).first()

    if not existing_viewing:
        raise HTTPException(status_code=404, detail="Viewing not found")

    if existing_viewing.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only cancel your own viewing requests")

    if existing_viewing.status not in (ViewingStatus.pending, ViewingStatus.accepted):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel a viewing with status '{existing_viewing.status.value}'"
        )

    existing_viewing.status = ViewingStatus.cancelled
    session.add(existing_viewing)
    session.commit()
    session.refresh(existing_viewing)

    user_obj = session.exec(
        select(users).where(users.id == user_id)
    ).first()

    existing_listing = session.exec(
        select(listing).where(listing.id == existing_viewing.listing_id)
    ).first()

    if user_obj and existing_listing:
        send_viewing_cancelled_email(
            email=user_obj.email,
            address=existing_listing.address,
            viewing_at=existing_viewing.viewing_at.strftime('%A %d %B %Y at %H:%M'),
            viewing_id=existing_viewing.id  # type: ignore
        )

    log_action(
        session=session,
        user_id=user_id,
        action="cancel_viewing",
        target_type="viewings",
        target_id=existing_viewing.id,
        success=True,
        status_code=200,
        details={"viewing_id": viewing_id, "listing_id": existing_viewing.listing_id}
    )
    session.commit()
    session.refresh(existing_viewing)

    return {
        "id": existing_viewing.id,
        "status": existing_viewing.status,
        "updated_at": existing_viewing.updated_at,
    }


@router.patch("/viewings/{viewing_id}/respond", response_model=ViewingStatusOut)
def respond_to_viewing(viewing_id: int, payload: RespondToViewing, user_id: int = Depends(get_current_user_id)):
    with Session(engine) as session:
        try:
            return respond_to_viewing_service(session, viewing_id, payload, user_id)
        except HTTPException as e:
            session.rollback()
            log_action(
                session=session,
                user_id=user_id,
                action="respond_to_viewing",
                target_type="viewings",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail), "viewing_id": viewing_id}
            )
            session.commit()
            raise


@router.patch("/viewings/{viewing_id}/cancel", response_model=ViewingStatusOut)
def cancel_viewing(viewing_id: int, user_id: int = Depends(get_current_user_id)):
    with Session(engine) as session:
        try:
            return cancel_viewing_service(session, viewing_id, user_id)
        except HTTPException as e:
            session.rollback()
            log_action(
                session=session,
                user_id=user_id,
                action="cancel_viewing",
                target_type="viewings",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail), "viewing_id": viewing_id}
            )
            session.commit()
            raise


def get_my_viewings_service(session: Session, user_id: int):

    my_viewings = session.exec(
        select(viewings).where(viewings.user_id == user_id)
    ).all()

    return {
        "viewings": [
            {
                "id": v.id,
                "user_id": v.user_id,
                "listing_id": v.listing_id,
                "message_id": v.message_id,
                "viewing_at": v.viewing_at,
                "status": v.status,
                "created_at": v.created_at,
                "updated_at": v.updated_at,
            }
            for v in my_viewings
        ],
        "total": len(my_viewings)
    }


def get_listing_viewings_service(session: Session, listing_id: int, user_id: int):

    existing_listing = session.exec(
        select(listing).where(listing.id == listing_id)
    ).first()

    if not existing_listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if existing_listing.created_by != user_id:
        raise HTTPException(status_code=403, detail="Only the listing owner can view viewing requests")

    listing_viewings = session.exec(
        select(viewings).where(viewings.listing_id == listing_id)
    ).all()

    return {
        "viewings": [
            {
                "id": v.id,
                "user_id": v.user_id,
                "listing_id": v.listing_id,
                "message_id": v.message_id,
                "viewing_at": v.viewing_at,
                "status": v.status,
                "created_at": v.created_at,
                "updated_at": v.updated_at,
            }
            for v in listing_viewings
        ],
        "total": len(listing_viewings)
    }


@router.get("/viewings/me", response_model=ViewingListOut)  # must be above /{viewing_id}
def get_my_viewings(user_id: int = Depends(get_current_user_id)):
    with Session(engine) as session:
        try:
            return get_my_viewings_service(session, user_id)
        except HTTPException as e:
            log_action(
                session=session,
                user_id=user_id,
                action="get_my_viewings",
                target_type="viewings",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail)}
            )
            session.commit()
            raise


@router.get("/listings/{listing_id}/viewings", response_model=ViewingListOut)
def get_listing_viewings(listing_id: int, user_id: int = Depends(get_current_user_id)):
    with Session(engine) as session:
        try:
            return get_listing_viewings_service(session, listing_id, user_id)
        except HTTPException as e:
            log_action(
                session=session,
                user_id=user_id,
                action="get_listing_viewings",
                target_type="viewings",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail), "listing_id": listing_id}
            )
            session.commit()
            raise