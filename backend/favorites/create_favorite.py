from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from auth.dependencies import get_current_user_id, require_customer
from server import engine
from .favorites_model import user_favorites as favorite, FavoriteOut
from listings.listings_model import listings as listing
from audit.audit import log_action

router = APIRouter()

@router.post("/favorites", response_model=FavoriteOut, status_code=201)
def create_favorite(listing_id: int, user_id: int = Depends(require_customer)):
    
    with Session(engine) as session:

        listing_obj = session.exec(
            select(listing).where(listing.id == listing_id)
        ).first()

        if not listing_obj:
            log_action(
                session = session,
                user_id=user_id,
                action="create_favorite",
                target_type="user_favorites",
                target_id=listing_id,
                success=False,
                status_code=404,
                details={"reason": "listing_not_found"}                
            )
            session.commit()
            raise HTTPException(status_code=404, detail="Listing not found")
        
        existing = session.exec(
            select(favorite).where(
                favorite.user_id == user_id,
                favorite.listing_id == listing_id
            )
        ).first()

        if existing:
            log_action(
                session = session,
                user_id=user_id,
                action="create_favorite",
                target_type="user_favorites",
                target_id=listing_id,
                success=False,
                status_code=409,
                details={"reason": "already_favorited"}
            )
            session.commit()
            raise HTTPException(status_code=409, detail="Already in favorites")

        new_favorite = favorite(
            user_id=user_id,
            listing_id=listing_id
        )
        session.add(new_favorite)
        session.commit()
        session.refresh(new_favorite)

        log_action(
            session=session,
            user_id=user_id,
            action="create_favorite",
            target_type="user_favorites",
            target_id=new_favorite.id,
            success=True,
            status_code=201
        )

        session.commit()

        return FavoriteOut(
            id=new_favorite.id, # type: ignore
            listing_id=new_favorite.listing_id,
            user_id=new_favorite.user_id
        )