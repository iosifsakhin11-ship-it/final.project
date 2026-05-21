from fastapi import HTTPException, Depends, Query, Header
from typing import Optional
from sqlmodel import Session, select
from server import engine
from .hash_token import hash_token
from .user_model import user_sessions as session_model
import bcrypt
from config.config import ENCODER
from .user_model import users

def get_current_user_id(
    token: Optional[str] = Query(None, description="Session token (query string)"),
    authorization: Optional[str] = Header(None, description="Bearer token (header)")
) -> int:
    """
    Accepts token via Authorization: Bearer <token> header OR ?token= query string.
    Header takes priority. This supports both modern (header) and legacy (query) clients.
    """
    actual_token = None
    if authorization and authorization.startswith("Bearer "):
        actual_token = authorization[7:]
    elif token:
        actual_token = token

    if not actual_token:
        raise HTTPException(status_code=401, detail="Authentication required")

    with Session(engine) as session:

        #hashing token to search db
        token_hash = hash_token(actual_token)

        #find user id by seraching the user_sessions table by:
        #token
        # wether the session is active or not
        statment = select(session_model).where(
            session_model.token == token_hash,
            session_model.revoked_at == None
        )
        user_search = session.exec(statment).first()

        #if there is a error with the token or it has been revoked rasie a exception
        if not user_search:
            raise HTTPException(status_code=401, detail="Invalid or revoked token")
        
        user = session.exec(
            select(users).where(users.id == user_search.user_id)
        ).first()

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        is_banned(user)
        
        return user_search.user_id
    
def require_customer(user_id: int = Depends(get_current_user_id)):
    with Session(engine) as session:
        user = session.exec(
            select(users).where(users.id == user_id)
        ).first()
        if user.type != "user": # type: ignore
            raise HTTPException(
                status_code=403,
                detail="Admins and supervisors cannot perform this action"
            )
        return user_id

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(ENCODER), bcrypt.gensalt()).decode(ENCODER)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(ENCODER), hashed_password.encode(ENCODER))

def is_banned(user: users):
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Your account has been banned")
        