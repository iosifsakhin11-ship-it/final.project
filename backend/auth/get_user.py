from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from auth.dependencies import get_current_user_id
from server import engine
from .user_model import users, userRead
from audit.audit import log_action

router = APIRouter()

def get_me_service(session: Session, user_id: int):

    user = session.exec(
        select(users).where(users.id == user_id)
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "type": user.type,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "is_verified": user.is_verified
    }


@router.get("/users/me", response_model=userRead, status_code=200)
def get_me(user_id: int = Depends(get_current_user_id)):
    with Session(engine) as session:
        try:
            return get_me_service(session, user_id)
        except HTTPException as e:
            log_action(
                session=session,
                user_id=user_id,
                action="get_me",
                target_type="users",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail)}
            )
            session.commit()
            raise