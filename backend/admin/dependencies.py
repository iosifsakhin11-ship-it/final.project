from auth.dependencies import get_current_user_id
from fastapi import Depends, HTTPException
from server import engine
from sqlmodel import Session, select
from auth.user_model import users

def require_admin(user_id: int = Depends(get_current_user_id)) -> int:
    with Session(engine) as session:
        user = session.exec(
            select(users).where(users.id == user_id)
        ).first()

        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        if user.type != "admin": # type: ignore
            raise HTTPException(
                status_code=403,
                detail="Only admins can perform this action"
            )
        return user_id