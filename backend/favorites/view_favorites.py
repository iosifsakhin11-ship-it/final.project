from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from auth.dependencies import get_current_user_id
from server import engine
from .favorites_model import user_favorites as favorite, FavoriteListResponse, FavoriteOut
from typing import List
from sqlmodel import func

router = APIRouter()

@router.get("/favorites", response_model=FavoriteListResponse, status_code=200)
def view_favorites(
    user_id: int = Depends(get_current_user_id),
    limit: int = 20,
    offset: int = 0    
):
    
    with Session(engine) as session:

        total = session.exec(
            select(func.count())
            .select_from(favorite)
            .where(favorite.user_id == user_id)
        ).one()

        query = (
            select(favorite)
            .where(favorite.user_id == user_id)
            .offset(offset)
            .limit(limit)
            )
        rows = session.exec(query).all()

        items = [
            FavoriteOut(
                id=f.id, # type: ignore
                listing_id=f.listing_id,
                user_id=f.user_id
            )
            for f in rows
        ]

        return FavoriteListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=items
        )