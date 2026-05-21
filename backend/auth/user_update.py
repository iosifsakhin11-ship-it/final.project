from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from .dependencies import get_current_user_id
from server import engine
from .user_model import users, userRead, UserUpdateRequest, ChangePasswordRequest
from audit.audit import log_action
from .dependencies import hash_password, verify_password

router = APIRouter()


def update_me_service(session: Session, user_id: int, data: UserUpdateRequest):

    user = session.exec(
        select(users).where(users.id == user_id)
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.username is not None:
        existing = session.exec(
            select(users).where(
                users.username == data.username,
                users.id != user_id
            )
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Username already taken")
        user.username = data.username

    if data.email is not None:
        existing = session.exec(
            select(users).where(
                users.email == data.email,
                users.id != user_id
            )
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already in use")
        user.email = data.email

    old_data = {"username": user.username, "email": user.email}

    session.add(user)
    session.commit()
    session.refresh(user)

    new_data = {"username": user.username, "email": user.email}
    changes = {
        key: {"old": old_data[key], "new": new_data[key]}
        for key in old_data
        if old_data[key] != new_data[key]
    }

    log_action(
        session=session,
        user_id=user_id,
        action="update_me",
        target_type="users",
        target_id=user_id,
        success=True,
        status_code=200,
        details={"changes": changes}
    )
    session.commit()

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "type": user.type,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "is_verified": user.is_verified
    }


def change_password_service(session: Session, user_id: int, data: ChangePasswordRequest):

    user = session.exec(
        select(users).where(users.id == user_id)
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(data.current_password, user.password_hash):
        log_action(
            session=session,
            user_id=user_id,
            action="change_password",
            target_type="users",
            target_id=user_id,
            success=False,
            status_code=401,
            details={"reason": "incorrect_current_password"}
        )
        session.commit()
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    if verify_password(data.new_password, user.password_hash):
        raise HTTPException(status_code=409, detail="New password must be different from current password")

    user.password_hash = hash_password(data.new_password)
    session.add(user)
    session.commit()

    log_action(
        session=session,
        user_id=user_id,
        action="change_password",
        target_type="users",
        target_id=user_id,
        success=True,
        status_code=200,
        details=None
    )
    session.commit()

    return {"message": "Password updated successfully"}


@router.patch("/users/me", response_model=userRead, status_code=200)
def update_me(data: UserUpdateRequest, user_id: int = Depends(get_current_user_id)):
    with Session(engine) as session:
        try:
            return update_me_service(session, user_id, data)
        except HTTPException as e:
            session.rollback()
            log_action(
                session=session,
                user_id=user_id,
                action="update_me",
                target_type="users",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail)}
            )
            session.commit()
            raise


@router.post("/users/me/change-password", status_code=200)
def change_password(data: ChangePasswordRequest, user_id: int = Depends(get_current_user_id)):
    with Session(engine) as session:
        try:
            return change_password_service(session, user_id, data)
        except HTTPException as e:
            session.rollback()
            log_action(
                session=session,
                user_id=user_id,
                action="change_password",
                target_type="users",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail)}
            )
            session.commit()
            raise