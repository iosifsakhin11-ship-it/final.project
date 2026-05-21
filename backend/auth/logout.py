from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from server import engine
from .hash_token import hash_token
from .user_model import user_sessions as session_model
from .user_model import LogoutResponse
from audit.audit import log_action

router = APIRouter()

@router.post("/logout", status_code=200, response_model=LogoutResponse)
def logout(token: str):

    token_hash = hash_token(token)

    with Session(engine) as session:
        statment = select(session_model).where(session_model.token == token_hash)
        session_to_revoke = session.exec(statment).first()

        if not session_to_revoke or session_to_revoke.revoked_at is not None:
            log_action(
                session=session,
                user_id=None,
                action="logout_failed",
                target_type="users",
                success=False,
                status_code=401,
                details={
                    "token_hash": token_hash,
                    "reason": "session_not_found/already_revoked"
                }
            )
            session.commit()

            raise HTTPException(status_code=401, detail="Session not found or already revoked")
    
        session_to_revoke.revoked_at = datetime.now(timezone.utc)
        session.add(session_to_revoke)
        session.commit()

        log_action(
            session=session,
            user_id=session_to_revoke.user_id,
            action="logout_success",
            target_type="users",
            target_id=session_to_revoke.user_id,
            success=True,
            status_code=200,
            details={
                "session_closed": True,
            }
        )
        session.commit()

    return LogoutResponse(message="logged out")