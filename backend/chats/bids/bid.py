from listings.listings_model import listings as listing
from chats.chats_model import messages as message, MessagePayload
from .bids_model import bids, BidStatus, CreateBid, BidOut, BidListOut, BidStatusOut, RespondToBid
from sqlmodel import Session, select
from audit.audit import log_action
from fastapi import HTTPException, APIRouter, Depends
from chats.create_chat import get_or_create_chat
from chats.send_message import message_service
from server import engine
from auth.dependencies import get_current_user_id, require_customer
from chats.viewings.viewings_model import viewings, ViewingStatus
from listings.listings_model import listingStatus
from auth.email_service import send_bid_cancelled_email, send_viewing_auto_cancelled_email, send_bid_accepted_email, send_bid_confirmation_email, send_bid_rejected_email, send_bid_auto_rejected_email
from auth.user_model import users
from payments.payments import create_payment_record

router = APIRouter()


def create_bid_service(session: Session, payload: CreateBid, user_id: int):

    existing_listing = session.exec(
        select(listing).where(listing.id == payload.listing_id)
    ).first()

    if not existing_listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if existing_listing.created_by == user_id:
        log_action(
            session=session,
            user_id=user_id,
            action="create_bid",
            target_type="bids",
            success=False,
            status_code=409,
            details={"reason": "attempted bid on own listing", "listing_id": payload.listing_id}
        )
        session.commit()
        raise HTTPException(status_code=409, detail="Cannot bid on your own listing")

    if existing_listing.status != listingStatus.ACTIVE:
        raise HTTPException(
            status_code=409,
            detail=f"This listing is no longer available"
        )

    existing_bid = session.exec(
        select(bids).where(
            bids.listing_id == payload.listing_id,
            bids.user_id == user_id,
            bids.status == BidStatus.pending
        )
    ).first()

    if existing_bid:
        log_action(
            session=session,
            user_id=user_id,
            action="create_bid",
            target_type="bids",
            success=False,
            status_code=409,
            details={"reason": "duplicate pending bid", "listing_id": payload.listing_id}
        )
        session.commit()
        raise HTTPException(status_code=409, detail="You already have a pending bid on this listing")

    new_bid = bids(
        user_id=user_id,
        listing_id=payload.listing_id,
        amount=payload.amount,
        payment_method=payload.payment_method    
    )
    session.add(new_bid)
    session.flush()

    bid_message_payload = MessagePayload(
        listing_id=payload.listing_id,
        content=f"I'd like to place a bid of £{payload.amount:.2f} on this listing."
    )

    sent_message = message_service(session, bid_message_payload, user_id)

    new_bid.message_id = sent_message["id"]
    session.add(new_bid)
    session.commit()
    session.refresh(new_bid)

    user_obj = session.exec(select(users).where(users.id == user_id)).first()

    send_bid_confirmation_email(
        email=user_obj.email, # type: ignore
        amount=float(payload.amount),
        address=existing_listing.address,
        bid_id=new_bid.id # type: ignore
    )

    log_action(
        session=session,
        user_id=user_id,
        action="create_bid",
        target_type="bids",
        target_id=new_bid.id,
        success=True,
        status_code=201,
        details={"amount": str(payload.amount), "listing_id": payload.listing_id}  # ← payload.amount
    )

    session.commit()
    session.refresh(new_bid)

    return {
        "id": new_bid.id,
        "user_id": new_bid.user_id,
        "listing_id": new_bid.listing_id,
        "message_id": new_bid.message_id,
        "amount": new_bid.amount,
        "status": new_bid.status,
        "payment_method": new_bid.payment_method,
        "created_at": new_bid.created_at,
        "updated_at": new_bid.updated_at,
    }


@router.post("/bids", response_model=BidOut, status_code=201)
def create_bid(payload: CreateBid, user_id: int = Depends(require_customer)):
    with Session(engine) as session:
        try:
            return create_bid_service(session, payload, user_id)
        except HTTPException as e:
            session.rollback()
            log_action(
                session=session,
                user_id=user_id,
                action="create_bid",
                target_type="bids",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail)}
            )
            session.commit()
            raise

def respond_to_bid_service(session: Session, bid_id: int, payload: RespondToBid, user_id: int):

    if payload.status not in (BidStatus.accepted, BidStatus.rejected):
        raise HTTPException(status_code=422, detail="Response must be accepted or rejected")

    existing_bid = session.exec(
        select(bids).where(bids.id == bid_id)
    ).first()

    if not existing_bid:
        raise HTTPException(status_code=404, detail="Bid not found")

    existing_listing = session.exec(
        select(listing).where(listing.id == existing_bid.listing_id)
    ).first()

    if existing_listing.created_by != user_id:  # type: ignore
        raise HTTPException(status_code=403, detail="Only the listing owner can respond to a bid")

    if existing_bid.status != BidStatus.pending:
        status_messages = {
            BidStatus.accepted:  "This bid has already been accepted",
            BidStatus.rejected:  "This bid has already been rejected",
            BidStatus.cancelled: "This bid has been withdrawn by the bidder",
        }
        raise HTTPException(
            status_code=409,
            detail=status_messages.get(existing_bid.status, "This bid cannot be responded to")
        )

    existing_bid.status = payload.status
    session.add(existing_bid)
    session.flush() 

    if payload.status == BidStatus.accepted:
        existing_listing.status = listingStatus.SOLD # type: ignore
        session.add(existing_listing)

        if existing_bid.payment_method:
            create_payment_record(
                session=session,
                user_id=existing_bid.user_id,
                bid_id=existing_bid.id, # type: ignore
                amount=float(existing_bid.amount),
                payment_method=existing_bid.payment_method
            )
    
        other_bids = session.exec(
            select(bids).where(
                bids.listing_id == existing_bid.listing_id,
                bids.id != existing_bid.id,
                bids.status == BidStatus.pending
            )
        ).all()

        for other_bid in other_bids:
            other_bid.status = BidStatus.rejected
            session.add(other_bid)

            other_bidder = session.exec(select(users).where(users.id == other_bid.user_id)).first()

            rejection_payload = MessagePayload(
                listing_id=existing_bid.listing_id,
                content=f"Your bid of £{other_bid.amount:.2f} has been rejected as another offer has been accepted."
            )
            message_service(session, rejection_payload, other_bid.user_id)

            if other_bidder:
                send_bid_auto_rejected_email(
                    email=other_bidder.email,
                    amount=float(other_bid.amount),
                    address=existing_listing.address, # type: ignore
                    bid_id=other_bid.id # type: ignore
                )

        other_viewings = session.exec(
            select(viewings).where(
                viewings.listing_id == existing_bid.listing_id,
                viewings.status == ViewingStatus.pending
            )
        ).all()

        for other_viewing in other_viewings:
            other_viewing.status = ViewingStatus.rejected
            session.add(other_viewing)

            viewing_user = session.exec(
                select(users).where(users.id == other_viewing.user_id)
            ).first()

            viewing_rejection_payload = MessagePayload(
                listing_id=existing_bid.listing_id,
                content=f"Your viewing request for {other_viewing.viewing_at.strftime('%A %d %B %Y at %H:%M')} has been cancelled as the listing has been accepted."
            )
            message_service(session, viewing_rejection_payload, other_viewing.user_id)

            if viewing_user:
                send_viewing_auto_cancelled_email(
                    email=viewing_user.email,
                    address=existing_listing.address, # type: ignore
                    viewing_at=other_viewing.viewing_at.strftime('%A %d %B %Y at %H:%M'),
                    viewing_id=other_viewing.id # type: ignore
                )

    session.commit()
    session.refresh(existing_bid)

    bidder = session.exec(
        select(users).where(users.id == existing_bid.user_id)
    ).first()

    response_word = "accepted" if payload.status == BidStatus.accepted else "rejected"
    notification_payload = MessagePayload(
        listing_id=existing_bid.listing_id,
        content=f"Your bid of £{existing_bid.amount:.2f} has been {response_word}."
    )
    message_service(session, notification_payload, existing_bid.user_id)

    if bidder:
        if payload.status == BidStatus.accepted:
            send_bid_accepted_email(
                email=bidder.email,
                amount=float(existing_bid.amount),
                address=existing_listing.address, # type: ignore
                bid_id=existing_bid.id # type: ignore
            )
        else:
            send_bid_rejected_email(
                email=bidder.email,
                amount=float(existing_bid.amount),
                address=existing_listing.address, # type: ignore
                bid_id=existing_bid.id # type: ignore
            )

    log_action(
        session=session,
        user_id=user_id,
        action="respond_to_bid",
        target_type="bids",
        target_id=existing_bid.id,
        success=True,
        status_code=200,
        details={
            "new_status": payload.status.value,
            "bid_id": bid_id,
            "listing_id": existing_bid.listing_id
        }
    )
    session.commit()
    session.refresh(existing_bid)

    return {
        "id": existing_bid.id,
        "status": existing_bid.status,
        "updated_at": existing_bid.updated_at,
    }


def cancel_bid_service(session: Session, bid_id: int, user_id: int):

    existing_bid = session.exec(
        select(bids).where(bids.id == bid_id)
    ).first()

    if not existing_bid:
        raise HTTPException(status_code=404, detail="Bid not found")

    if existing_bid.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only cancel your own bids")

    if existing_bid.status not in (BidStatus.pending, BidStatus.accepted):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel a bid with status '{existing_bid.status.value}'"
        )

    existing_bid.status = BidStatus.cancelled
    session.add(existing_bid)
    session.commit()
    session.refresh(existing_bid)

    user_obj = session.exec(
        select(users).where(users.id == user_id)
    ).first()

    existing_listing = session.exec(
        select(listing).where(listing.id == existing_bid.listing_id)
    ).first()

    if user_obj and existing_listing:
        send_bid_cancelled_email(
            email=user_obj.email,
            amount=float(existing_bid.amount),
            address=existing_listing.address,
            bid_id=existing_bid.id # type: ignore
        )

    log_action(
        session=session,
        user_id=user_id,
        action="cancel_bid",
        target_type="bids",
        target_id=existing_bid.id,
        success=True,
        status_code=200,
        details={"bid_id": bid_id, "listing_id": existing_bid.listing_id}
    )
    session.commit()
    session.refresh(existing_bid)

    return {
        "id": existing_bid.id,
        "user_id": existing_bid.user_id,
        "listing_id": existing_bid.listing_id,
        "message_id": existing_bid.message_id,
        "amount": existing_bid.amount,
        "status": existing_bid.status,
        "created_at": existing_bid.created_at,
        "updated_at": existing_bid.updated_at,
    }


@router.patch("/bids/{bid_id}/respond", response_model=BidStatusOut)
def respond_to_bid(bid_id: int, payload: RespondToBid, user_id: int = Depends(get_current_user_id)):
    with Session(engine) as session:
        try:
            return respond_to_bid_service(session, bid_id, payload, user_id)
        except HTTPException as e:
            session.rollback()
            log_action(
                session=session,
                user_id=user_id,
                action="respond_to_bid",
                target_type="bids",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail), "bid_id": bid_id}
            )
            session.commit()
            raise


@router.patch("/bids/{bid_id}/cancel", response_model=BidStatusOut)
def cancel_bid(bid_id: int, user_id: int = Depends(get_current_user_id)):
    with Session(engine) as session:
        try:
            return cancel_bid_service(session, bid_id, user_id)
        except HTTPException as e:
            session.rollback()
            log_action(
                session=session,
                user_id=user_id,
                action="cancel_bid",
                target_type="bids",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail), "bid_id": bid_id}
            )
            session.commit()
            raise


def get_my_bids_service(session: Session, user_id: int):

    my_bids = session.exec(
        select(bids).where(bids.user_id == user_id)
    ).all()

    return {
        "bids": [
            {
                "id": bid.id,
                "user_id": bid.user_id,
                "listing_id": bid.listing_id,
                "message_id": bid.message_id,
                "amount": bid.amount,
                "status": bid.status,
                "payment_method": bid.payment_method,
                "created_at": bid.created_at,
                "updated_at": bid.updated_at,
            }
            for bid in my_bids
        ],
        "total": len(my_bids)
    }


def get_listing_bids_service(session: Session, listing_id: int, user_id: int):

    existing_listing = session.exec(
        select(listing).where(listing.id == listing_id)
    ).first()

    if not existing_listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if existing_listing.created_by != user_id:
        raise HTTPException(status_code=403, detail="Only the listing owner can view bids on this listing")

    listing_bids = session.exec(
        select(bids).where(bids.listing_id == listing_id)
    ).all()

    return {
        "bids": [
            {
                "id": bid.id,
                "user_id": bid.user_id,
                "listing_id": bid.listing_id,
                "message_id": bid.message_id,
                "amount": bid.amount,
                "status": bid.status,
                "payment_method": bid.payment_method,
                "created_at": bid.created_at,
                "updated_at": bid.updated_at,
            }
            for bid in listing_bids
        ],
        "total": len(listing_bids)
    }


@router.get("/bids/me", response_model=BidListOut)
def get_my_bids(user_id: int = Depends(get_current_user_id)):
    with Session(engine) as session:
        try:
            return get_my_bids_service(session, user_id)
        except HTTPException as e:
            log_action(
                session=session,
                user_id=user_id,
                action="get_my_bids",
                target_type="bids",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail)}
            )
            session.commit()
            raise


@router.get("/listings/{listing_id}/bids", response_model=BidListOut)
def get_listing_bids(listing_id: int, user_id: int = Depends(get_current_user_id)):
    with Session(engine) as session:
        try:
            return get_listing_bids_service(session, listing_id, user_id)
        except HTTPException as e:
            log_action(
                session=session,
                user_id=user_id,
                action="get_listing_bids",
                target_type="bids",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail), "listing_id": listing_id}
            )
            session.commit()
            raise