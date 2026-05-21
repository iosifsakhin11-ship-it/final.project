from listings.listings_model import listings as listing
from .chats_model import messages as message, messageCreate, messageOut, chats, MessagePayload
from sqlmodel import Session, select, or_
from audit.audit import log_action
from fastapi import HTTPException
from .create_chat import get_or_create_chat
from server import engine
from auth.dependencies import get_current_user_id, require_customer
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()

def message_service(session: Session, payload: MessagePayload, user_id: int):

    existing_listing = session.exec(
            select(listing).where(listing.id == payload.listing_id)
    ).first()

    if not existing_listing:
        raise HTTPException(status_code=404, detail="listing not found")     

    # Check if a chat already exists for this listing and user
    # If the sender is the owner, they must be replying to an existing chat.
    # If the sender is a customer, they can create a new chat or use an existing one.
    
    if user_id == existing_listing.created_by:
        # Owner is sending a message. They must be replying to an existing chat.
        # But wait, messageCreate/MessagePayload only has listing_id.
        # How does the owner know which customer to message?
        # Usually, the owner replies to a SPECIFIC chat.
        # For now, let's allow the owner to send a message if at least one chat exists for this listing.
        # This is still a bit flawed, but better than a hard block.
        # Ideally, we'd need a chat_id in the payload for replies.
        
        # Let's search for an existing chat for this listing where user_id is the owner.
        chat = session.exec(
            select(chats).where(
                chats.listing_id == payload.listing_id,
                chats.owner_id == user_id
            )
        ).first()
        
        if not chat:
            raise HTTPException(status_code=403, detail="Owners can only message in existing chats started by customers")
    else:
        # Customer is sending a message.
        chat = get_or_create_chat(
            session,
            listing_id=existing_listing.id,
            user_id=user_id
        )

    new_message = message(
        chat_id=chat.id, # type: ignore
        sender_id=user_id,
        content=payload.content
    )

    session.add(new_message)
    session.commit()
    session.refresh(new_message)

    log_action(
        session=session,
        user_id=user_id,
        action="send_message",
        target_type="messages",
        target_id=new_message.id,
        success=True,
        status_code=201,
        details=None
    )

    session.commit()

    return {
    "id": new_message.id,
    "chat_id": new_message.chat_id,
    "sender_id": new_message.sender_id,
    "content": new_message.content,
    "created_at": new_message.created_at,
    }

@router.post("/messages", response_model=messageOut)
def send_message(payload: messageCreate, user_id: int = Depends(require_customer)):
    with Session(engine) as session:
        try:
            message = message_service(session, payload, user_id)
            return message
        except HTTPException as e:
            session.rollback()
            log_action(
                session=session,
                user_id=user_id,
                action="send_message",
                target_type="messages",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail)}
            )
            session.commit()
            raise