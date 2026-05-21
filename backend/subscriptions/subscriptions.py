from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy import or_
from server import engine
from auth.dependencies import get_current_user_id, require_customer
from listings.listings_model import listings as listing
from favorites.favorites_model import user_favorites as favourite
from .subscriptions_model import listing_subscriptions, SubscriptionOut, SubscriptionListOut, CreateSubscription
from auth.email_service import send_listing_notification_email
from audit.audit import log_action
from decimal import Decimal

router = APIRouter()


def create_subscription_service(session: Session, payload: CreateSubscription, user_id: int):

    if payload.favourite_id is not None:
        fav = session.exec(
            select(favourite).where(
                favourite.id == payload.favourite_id,
                favourite.user_id == user_id
            )
        ).first()

        if not fav:
            raise HTTPException(status_code=404, detail="Favourite not found")

        fav_listing = session.exec(
            select(listing).where(listing.id == fav.listing_id)
        ).first()

        if not fav_listing:
            raise HTTPException(status_code=404, detail="Listing not found")

        category  = payload.category  or fav_listing.category
        bedrooms  = payload.bedrooms  or fav_listing.bedrooms
        min_price = payload.min_price or Decimal(str(float(fav_listing.price) * 0.8))
        max_price = payload.max_price or Decimal(str(float(fav_listing.price) * 1.2))
    else:
        category  = payload.category
        bedrooms  = payload.bedrooms
        min_price = payload.min_price
        max_price = payload.max_price

    if payload.favourite_id is not None:
        existing = session.exec(
            select(listing_subscriptions).where(
                listing_subscriptions.user_id      == user_id,
                listing_subscriptions.favourite_id == payload.favourite_id
            )
        ).first()

        if existing:
            raise HTTPException(status_code=409, detail="You already have a subscription for this favourite")

    new_sub = listing_subscriptions(
        user_id=user_id,
        favourite_id=payload.favourite_id,
        category=category,
        min_price=min_price,
        max_price=max_price,
        bedrooms=bedrooms
    )
    session.add(new_sub)
    session.commit()
    session.refresh(new_sub)

    log_action(
        session=session,
        user_id=user_id,
        action="create_subscription",
        target_type="listing_subscriptions",
        target_id=new_sub.id,
        success=True,
        status_code=201,
        details={
            "favourite_id": payload.favourite_id,
            "category": category,
            "bedrooms": bedrooms,
        }
    )
    session.commit()

    return {
        "id": new_sub.id,
        "user_id": new_sub.user_id,
        "favourite_id": new_sub.favourite_id,
        "category": new_sub.category,
        "min_price": new_sub.min_price,
        "max_price": new_sub.max_price,
        "bedrooms": new_sub.bedrooms,
        "created_at": new_sub.created_at,
    }


def get_my_subscriptions_service(session: Session, user_id: int):
    subs = session.exec(
        select(listing_subscriptions).where(
            listing_subscriptions.user_id == user_id
        )
    ).all()

    return {
        "subscriptions": [
            {
                "id": s.id,
                "user_id": s.user_id,
                "favourite_id": s.favourite_id,
                "category": s.category,
                "min_price": s.min_price,
                "max_price": s.max_price,
                "bedrooms": s.bedrooms,
                "created_at": s.created_at,
            }
            for s in subs
        ],
        "total": len(subs)
    }


def delete_subscription_service(session: Session, subscription_id: int, user_id: int):
    sub = session.exec(
        select(listing_subscriptions).where(
            listing_subscriptions.id == subscription_id,
            listing_subscriptions.user_id == user_id
        )
    ).first()

    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    info = {"id": sub.id, "category": sub.category}

    session.delete(sub)
    session.commit()

    log_action(
        session=session,
        user_id=user_id,
        action="delete_subscription",
        target_type="listing_subscriptions",
        target_id=subscription_id,
        success=True,
        status_code=200,
        details={"deleted_subscription": info}
    )
    session.commit()

    return {"deleted": True, "subscription_id": subscription_id}


def notify_subscribers(session: Session, new_listing: listing):
    all_subs = session.exec(
        select(listing_subscriptions).where(
            listing_subscriptions.user_id != new_listing.created_by
        )
    ).all()

    for sub in all_subs:
        if sub.category and sub.category != new_listing.category:
            continue
        if sub.bedrooms and sub.bedrooms != new_listing.bedrooms:
            continue
        if sub.min_price and new_listing.price < sub.min_price:
            continue
        if sub.max_price and new_listing.price > sub.max_price:
            continue

        from auth.user_model import users
        user_obj = session.exec(
            select(users).where(users.id == sub.user_id)
        ).first()

        if user_obj:
            send_listing_notification_email(
                email=user_obj.email,
                listing_id=new_listing.id, # type: ignore
                address=new_listing.address,
                category=new_listing.category,
                price=float(new_listing.price)
            )


@router.post("/subscriptions", response_model=SubscriptionOut, status_code=201)
def create_subscription(payload: CreateSubscription, user_id: int = Depends(require_customer)):
    with Session(engine) as session:
        try:
            return create_subscription_service(session, payload, user_id)
        except HTTPException as e:
            session.rollback()
            log_action(
                session=session,
                user_id=user_id,
                action="create_subscription",
                target_type="listing_subscriptions",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail)}
            )
            session.commit()
            raise


@router.get("/subscriptions/me", response_model=SubscriptionListOut)
def get_my_subscriptions(user_id: int = Depends(require_customer)):
    with Session(engine) as session:
        return get_my_subscriptions_service(session, user_id)


@router.delete("/subscriptions/{subscription_id}", status_code=200)
def delete_subscription(subscription_id: int, user_id: int = Depends(require_customer)):
    with Session(engine) as session:
        try:
            return delete_subscription_service(session, subscription_id, user_id)
        except HTTPException as e:
            session.rollback()
            log_action(
                session=session,
                user_id=user_id,
                action="delete_subscription",
                target_type="listing_subscriptions",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail)}
            )
            session.commit()
            raise