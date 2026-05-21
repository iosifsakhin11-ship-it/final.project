from sqlmodel import Session, select
from sqlalchemy import desc
from fastapi import HTTPException

from .chats_model import chats, messages
from listings.listings_model import listings

from fastapi import APIRouter, Depends
from sqlmodel import Session
from server import engine
from auth.dependencies import get_current_user_id


def get_user_chats(session: Session, user_id: int):

    user_chats = session.exec(
        select(chats).where(
            (chats.customer_id == user_id) |
            (chats.owner_id == user_id)
        )
    ).all()

    if not user_chats:
        return []

    result = []

    for chat in user_chats:

        last_message = session.exec(
            select(messages)
            .where(messages.chat_id == chat.id)
            .limit(1)
        ).first()

        other_user_id = (
            chat.owner_id
            if chat.customer_id == user_id
            else chat.customer_id
        )

        result.append({
            "chat_id": chat.id,
            "listing_id": chat.listing_id,
            "other_user_id": other_user_id,
            "last_message": last_message.content if last_message else None,
            "last_message_time": last_message.created_at if last_message else None,
            "updated_at": chat.created_at
        })

    return result

router = APIRouter()


@router.get("/chats")
def get_chats(user_id: int = Depends(get_current_user_id)):

    with Session(engine) as session:
        return get_user_chats(session, user_id)