from fastapi import APIRouter, Depends, HTTPException
from .chats_model import chats, chatOut, messages, ChatDetailOut
from sqlmodel import Session, select
from server import engine
from auth.dependencies import get_current_user_id
from audit.audit import log_action
from listings.listings_model import listings as listing
from sqlalchemy.exc import IntegrityError
from sqlalchemy import asc
from sqlmodel import col

router = APIRouter()

def get_chat_service(session: Session, chat_id: int, user_id: int):

    existing_chat = session.exec(
        select(chats).where(chats.id == chat_id)
    ).first()

    if not existing_chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    if existing_chat.customer_id != user_id and existing_chat.owner_id != user_id:
        raise HTTPException(status_code=403, detail="You do not have access to this chat")

    chat_messages = session.exec(
        select(messages)
        .where(messages.chat_id == chat_id)
        .order_by(col(messages.created_at).asc())
    ).all()

    return {
        "id": existing_chat.id,
        "listing_id": existing_chat.listing_id,
        "customer_id": existing_chat.customer_id,
        "owner_id": existing_chat.owner_id,
        "created_at": existing_chat.created_at,
        "messages": [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "content": m.content,
                "created_at": m.created_at,
            }
            for m in chat_messages
        ],
        "total_messages": len(chat_messages)
    }


@router.get("/chats/{chat_id}", response_model=ChatDetailOut)
def get_chat(chat_id: int, user_id: int = Depends(get_current_user_id)):
    with Session(engine) as session:
        try:
            return get_chat_service(session, chat_id, user_id)
        except HTTPException as e:
            log_action(
                session=session,
                user_id=user_id,
                action="get_chat",
                target_type="chats",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail), "chat_id": chat_id}
            )
            session.commit()
            raise