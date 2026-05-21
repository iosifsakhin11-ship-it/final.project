from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from auth.dependencies import get_current_user_id, require_customer
from server import engine
from .favorites_model import user_favorites as favorite
from listings.listings_model import listings as listing
from audit.audit import log_action

router = APIRouter()

@router.delete("/favorites/{listing_id}", status_code=200)
def delete_favorite(listing_id: int, user_id: int = Depends(require_customer)):
    
    with Session(engine) as session:

        favorite_statment = select(favorite).where(
            favorite.user_id == user_id,
            favorite.listing_id == listing_id
        )
        favorite_row = session.exec(favorite_statment).first()

        if not favorite_row:
            log_action(
                    session= session,
                    user_id = user_id,
                    action="delete_favorite",
                    target_type="user_favorites",
                    success=False,
                    status_code=404,
                    details={"reason": "favorite_not_found"}
                )
            session.commit()

            raise HTTPException(status_code=404, detail="Favorite not found")
        
        info = {
            "id": favorite_row.id,
            "user_id": favorite_row.user_id,
            "listing_id": favorite_row.listing_id
        }

        session.delete(favorite_row)
        session.commit()

        log_action(
            session= session,
            user_id=user_id,
            action="delete_favorite",
            target_type="user_favorites",
            target_id=info["id"],
            success=True,
            status_code=200,
            details={"deleted_object": info}
        )
        session.commit()

        return {
            "deleted": True,
            "favorite_id": info["id"]
        }
