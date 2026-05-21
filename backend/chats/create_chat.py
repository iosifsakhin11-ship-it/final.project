from fastapi import APIRouter, Depends, HTTPException
from .chats_model import chats, chatOut
from sqlmodel import Session, select
from server import engine
from auth.dependencies import get_current_user_id
from audit.audit import log_action
from listings.listings_model import listings as listing
from sqlalchemy.exc import IntegrityError

def get_or_create_chat(session, listing_id, user_id):

    exists_listing = session.get(listing, listing_id)
    if not exists_listing:
        raise HTTPException(404, "Listing not found")
    
    owner_id = exists_listing.created_by

    chat = session.exec(
        select(chats).where(
            chats.listing_id == listing_id,
            chats.customer_id == user_id,
        )
    ).first()

    if chat:
        return chat
    
    chat = chats(
        listing_id=listing_id,
        customer_id=user_id,
        owner_id=owner_id
    )

    session.add(chat)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        return session.exec(
            select(chats).where(
                chats.listing_id == listing_id,
                chats.customer_id == user_id,
            )
        ).first()

    return chat

"""
    existing_listing = session.exec(
        select(listing).where(listing.id == listing_id)
    ).first()

    if not existing_listing:
        log_action(
            session=session,
            user_id=user_id,
            action="create_chat",
            target_type="chats",
            success=False,
            status_code=404,
            details={"reason": "listing not found"}
        )
        session.commit()
        raise HTTPException(status_code=404, detail="listing not found")           

    if user_id == existing_listing.created_by: # type: ignore
        log_action(
            session=session,
            user_id=user_id,
            action="create_chat",
            target_type="chats",
            success=False,
            status_code=409,
            details={"reason": "Cannot create chat with your own listing"}
        )
        session.commit()
        raise HTTPException(status_code=409, detail="Cannot create chat with your own listing")
        
    existing_chat = session.exec(
        select(new_chats).where(
            (new_chats.listing_id == listing_id) &
            (new_chats.customer_id == user_id) &
            (new_chats.owner_id == existing_listing.created_by) # type: ignore
        )
    ).first()

    if existing_chat:
        log_action(
            session=session,
            user_id=user_id,
            action="create_chat",
            target_type="chats",
            success=False,
            status_code=409,
            details={"reason": "chat already exists"}
        )
        session.commit()
        raise HTTPException(status_code=409, detail="Chat already exists")
        
    new_chat = new_chats(
        listing_id=listing_id,
        customer_id=user_id,
        owner_id=existing_listing.created_by # type: ignore
    )

    session.add(new_chat)
    session.commit()
    session.refresh(new_chat)

    log_action(
        session=session,
        user_id=user_id,
        action="create_chat",
        target_type="chats",
        target_id=new_chat.id,
        success=True,
        status_code=201
    )

    session.commit()

    return newChatOut(
        id = new_chat.id, # type: ignore
        listing_id=new_chat.listing_id,
        customer_id=new_chat.customer_id,
        owner_id=new_chat.owner_id,
        created_at=new_chat.created_at
    )
"""