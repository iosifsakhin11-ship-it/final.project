from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func, col
from sqlalchemy import and_, extract
from datetime import datetime
from server import engine
from auth.dependencies import get_current_user_id
from auth.user_model import users
from listings.listings_model import listings as listing
from chats.chats_model import messages, chats
from chats.bids.bids_model import bids, BidStatus
from chats.viewings.viewings_model import viewings
from .reports_model import SearchTrendsReportOut, FilterTrendOut, InquiryReportOut, ListingActivityOut, MonthlyTrendOut, ListingFavouriteStatsOut, MonthlyFavouriteTrendOut, SavedListingsReportOut
from audit.audit import log_action
from favorites.favorites_model import user_favorites
from audit.audit import log_action
from audit.audit_logs_model import AuditLog

router = APIRouter()


def require_supervisor(user_id: int = Depends(get_current_user_id)):
    with Session(engine) as session:
        user = session.exec(
            select(users).where(users.id == user_id)
        ).first()
        if user.type not in ("supervisor", "admin"): # type: ignore
            raise HTTPException(status_code=403, detail="Supervisors only")
        return user_id


def parse_month(month_str: str, param_name: str) -> datetime:
    try:
        return datetime.strptime(month_str, "%Y-%m")
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"{param_name} must be in format YYYY-MM e.g. 2026-04"
        )


def get_inquiry_report_service(session: Session, from_month: str, to_month: str):

    from_dt = parse_month(from_month, "from_month")
    to_dt   = parse_month(to_month, "to_month")

    if from_dt > to_dt:
        raise HTTPException(status_code=422, detail="from_month cannot be after to_month")

    total_messages = session.exec(
        select(func.count()).select_from(messages).where(
            messages.created_at >= from_dt,
            messages.created_at < to_dt
        )
    ).one()

    total_bids = session.exec(
        select(func.count()).select_from(bids).where(
            bids.created_at >= from_dt,
            bids.created_at < to_dt
        )
    ).one()

    total_viewings = session.exec(
        select(func.count()).select_from(viewings).where(
            viewings.created_at >= from_dt,
            viewings.created_at < to_dt
        )
    ).one()

    all_listings = session.exec(select(listing)).all()

    listing_activity = []
    for l in all_listings:

        listing_id = l.id

        msg_count = session.exec(
            select(func.count()).select_from(messages)
            .join(chats, col(chats.id) == col(messages.chat_id))
            .where(
                col(chats.listing_id) == listing_id,
                col(messages.created_at) >= from_dt,
                col(messages.created_at) < to_dt
            )
        ).one()

        bid_count = session.exec(
            select(func.count()).select_from(bids).where(
                bids.listing_id == l.id,
                bids.created_at >= from_dt,
                bids.created_at < to_dt
            )
        ).one()

        viewing_count = session.exec(
            select(func.count()).select_from(viewings).where(
                viewings.listing_id == l.id,
                viewings.created_at >= from_dt,
                viewings.created_at < to_dt
            )
        ).one()

        total = msg_count + bid_count + viewing_count
        if total > 0:
            listing_activity.append(
                ListingActivityOut(
                    listing_id=l.id,  # type: ignore
                    address=l.address,
                    messages=msg_count,
                    bids=bid_count,
                    viewings=viewing_count,
                    total_activity=total
                )
            )

    listing_activity.sort(key=lambda x: x.total_activity, reverse=True)

    monthly_trends = []
    current = from_dt
    while current <= to_dt:
        month_str = current.strftime("%Y-%m")
        next_month = datetime(
            current.year + (current.month // 12),
            ((current.month % 12) + 1),
            1
        )

        month_messages = session.exec(
            select(func.count()).select_from(messages).where(
                messages.created_at >= current,
                messages.created_at < next_month
            )
        ).one()

        month_bids = session.exec(
            select(func.count()).select_from(bids).where(
                bids.created_at >= current,
                bids.created_at < next_month
            )
        ).one()

        month_viewings = session.exec(
            select(func.count()).select_from(viewings).where(
                viewings.created_at >= current,
                viewings.created_at < next_month
            )
        ).one()

        monthly_trends.append(MonthlyTrendOut(
            month=month_str,
            messages=month_messages,
            bids=month_bids,
            viewings=month_viewings
        ))

        current = next_month

    return {
        "from_month": from_month,
        "to_month": to_month,
        "summary": {
            "total_messages": total_messages,
            "total_bids": total_bids,
            "total_viewings": total_viewings,
        },
        "most_inquired_listings": listing_activity[:10], 
        "monthly_trends": monthly_trends
    }


@router.get("/reports/inquiries", response_model=InquiryReportOut)
def get_inquiry_report(
    from_month: str = Query(..., example="2026-01"),
    to_month: str = Query(..., example="2026-04"),
    user_id: int = Depends(require_supervisor)
):
    with Session(engine) as session:
        try:
            return get_inquiry_report_service(session, from_month, to_month)
        except HTTPException as e:
            log_action(
                session=session,
                user_id=user_id,
                action="get_inquiry_report",
                target_type="reports",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail)}
            )
            session.commit()
            raise

def get_saved_listings_report_service(session: Session, from_month: str, to_month: str):

    from_dt = parse_month(from_month, "from_month")
    to_dt   = parse_month(to_month, "to_month")

    if from_dt > to_dt:
        raise HTTPException(status_code=422, detail="from_month cannot be after to_month")

    total_favourites = session.exec(
        select(func.count()).select_from(user_favorites).where(
            col(user_favorites.created_at) >= from_dt,
            col(user_favorites.created_at) < to_dt
        )
    ).one()

    unique_listings_saved = session.exec(
        select(func.count()).select_from(
            select(user_favorites.listing_id)
            .where(
                col(user_favorites.created_at) >= from_dt,
                col(user_favorites.created_at) < to_dt
            )
            .distinct()
            .subquery()
        )
    ).one()

    unique_users_saving = session.exec(
        select(func.count()).select_from(
            select(user_favorites.user_id)
            .where(
                col(user_favorites.created_at) >= from_dt,
                col(user_favorites.created_at) < to_dt
            )
            .distinct()
            .subquery()
        )
    ).one()

    all_listings = session.exec(select(listing)).all()

    listing_stats = []
    for l in all_listings:
        listing_id = l.id

        fav_count = session.exec(
            select(func.count()).select_from(user_favorites).where(
                col(user_favorites.listing_id) == listing_id,
                col(user_favorites.created_at) >= from_dt,
                col(user_favorites.created_at) < to_dt
            )
        ).one()

        if fav_count > 0:
            listing_stats.append(
                ListingFavouriteStatsOut(
                    listing_id=listing_id,  # type: ignore
                    address=l.address,
                    category=l.category,
                    price=float(l.price),
                    total_favourites=fav_count
                )
            )

    listing_stats.sort(key=lambda x: x.total_favourites, reverse=True)

    monthly_trends = []
    current = from_dt
    while current <= to_dt:
        month_str  = current.strftime("%Y-%m")
        next_month = datetime(
            current.year + (current.month // 12),
            ((current.month % 12) + 1),
            1
        )

        month_favs = session.exec(
            select(func.count()).select_from(user_favorites).where(
                col(user_favorites.created_at) >= current,
                col(user_favorites.created_at) < next_month
            )
        ).one()

        monthly_trends.append(MonthlyFavouriteTrendOut(
            month=month_str,
            total_favourites=month_favs
        ))

        current = next_month

    return {
        "from_month": from_month,
        "to_month": to_month,
        "summary": {
            "total_favourites": total_favourites,
            "unique_listings_saved": unique_listings_saved,
            "unique_users_saving": unique_users_saving
        },
        "most_saved_listings": listing_stats[:10],
        "monthly_trends": monthly_trends
    }


@router.get("/reports/saved-listings", response_model=SavedListingsReportOut)
def get_saved_listings_report(
    from_month: str = Query(..., example="2026-01"),
    to_month: str = Query(..., example="2026-04"),
    user_id: int = Depends(require_supervisor)
):
    with Session(engine) as session:
        try:
            return get_saved_listings_report_service(session, from_month, to_month)
        except HTTPException as e:
            log_action(
                session=session,
                user_id=user_id,
                action="get_saved_listings_report",
                target_type="reports",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail)}
            )
            session.commit()
            raise

def get_search_trends_service(session: Session, from_month: str, to_month: str):

    from_dt = parse_month(from_month, "from_month")
    to_dt   = parse_month(to_month, "to_month")

    if from_dt > to_dt:
        raise HTTPException(status_code=422, detail="from_month cannot be after to_month")

    search_logs = session.exec(
        select(AuditLog).where(
            AuditLog.action == "search_listings",
            col(AuditLog.created_at) >= from_dt,
            col(AuditLog.created_at) < to_dt
        )
    ).all()

    total_searches = len(search_logs)

    category_counts = {}
    type_counts = {}
    bedroom_counts = {}
    price_min_values = []
    price_max_values = []

    for log in search_logs:
        if not log.details:
            continue

        details = log.details 
        if details.get("category"):
            val = details["category"]
            category_counts[val] = category_counts.get(val, 0) + 1

        if details.get("type"):
            val = details["type"]
            type_counts[val] = type_counts.get(val, 0) + 1

        if details.get("bedrooms"):
            val = str(details["bedrooms"])
            bedroom_counts[val] = bedroom_counts.get(val, 0) + 1

        if details.get("min_price"):
            price_min_values.append(float(details["min_price"]))

        if details.get("max_price"):
            price_max_values.append(float(details["max_price"]))

    popular_categories = sorted(
        [FilterTrendOut(filter_value=k, count=v) for k, v in category_counts.items()],
        key=lambda x: x.count, reverse=True
    )

    popular_types = sorted(
        [FilterTrendOut(filter_value=k, count=v) for k, v in type_counts.items()],
        key=lambda x: x.count, reverse=True
    )

    popular_bedrooms = sorted(
        [FilterTrendOut(filter_value=k, count=v) for k, v in bedroom_counts.items()],
        key=lambda x: x.count, reverse=True
    )

    price_ranges = {
        "avg_min_price": round(sum(price_min_values) / len(price_min_values), 2) if price_min_values else None,
        "avg_max_price": round(sum(price_max_values) / len(price_max_values), 2) if price_max_values else None,
        "lowest_min": min(price_min_values) if price_min_values else None,
        "highest_max": max(price_max_values) if price_max_values else None,
    }

    monthly_trends = []
    current = from_dt
    while current <= to_dt:
        month_str  = current.strftime("%Y-%m")
        next_month = datetime(
            current.year + (current.month // 12),
            ((current.month % 12) + 1),
            1
        )

        month_logs = [
            log for log in search_logs
            if current <= log.created_at < next_month
        ]

        month_categories = {}
        for log in month_logs:
            if log.details and log.details.get("category"):
                val = log.details["category"]
                month_categories[val] = month_categories.get(val, 0) + 1

        monthly_trends.append({
            "month": month_str,
            "total_searches": len(month_logs),
            "top_category": max(month_categories, key=month_categories.get) if month_categories else None, # type: ignore
        })

        current = next_month

    return {
        "from_month": from_month,
        "to_month": to_month,
        "summary": {
            "total_searches": total_searches,
            "unique_filters_used": len([l for l in search_logs if l.details]),
            "most_searched_category": popular_categories[0].filter_value if popular_categories else None,
            "most_searched_type": popular_types[0].filter_value if popular_types else None,
        },
        "popular_categories": popular_categories,
        "popular_types": popular_types,
        "popular_bedrooms": popular_bedrooms,
        "price_ranges": price_ranges,
        "monthly_trends": monthly_trends
    }


@router.get("/reports/search-trends", response_model=SearchTrendsReportOut)
def get_search_trends(
    from_month: str = Query(..., example="2026-01"),
    to_month: str = Query(..., example="2026-04"),
    user_id: int = Depends(require_supervisor)
):
    with Session(engine) as session:
        try:
            return get_search_trends_service(session, from_month, to_month)
        except HTTPException as e:
            log_action(
                session=session,
                user_id=user_id,
                action="get_search_trends",
                target_type="reports",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail)}
            )
            session.commit()
            raise