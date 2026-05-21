from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy import func
from server import engine
from auth.user_model import users
from audit.audit import log_action
from .dependencies import require_admin
from typing import Optional
from .admins_models import AdminUserUpdate, AdminUserRead, AdminUserListResponse

router = APIRouter()


def admin_update_user_service(session: Session, target_id: int, data: AdminUserUpdate, admin_id: int):

    target_user = session.exec(
        select(users).where(users.id == target_id)
    ).first()

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_id == admin_id:
        raise HTTPException(status_code=409, detail="You cannot update your own account via admin panel")

    if target_user.type == "admin" and data.is_banned:
        raise HTTPException(status_code=409, detail="Cannot ban another admin")

    old_data = {
        "type": target_user.type,
        "is_banned": target_user.is_banned,
        "is_verified": target_user.is_verified
    }

    if data.type is not None:
        target_user.type = data.type

    if data.is_banned is not None:
        target_user.is_banned = data.is_banned

    if data.is_verified is not None:
        target_user.is_verified = data.is_verified

    session.add(target_user)
    session.commit()
    session.refresh(target_user)

    new_data = {
        "type": target_user.type,
        "is_banned": target_user.is_banned,
        "is_verified": target_user.is_verified
    }

    changes = {
        key: {"old": old_data[key], "new": new_data[key]}
        for key in old_data
        if old_data[key] != new_data[key]
    }

    log_action(
        session=session,
        user_id=admin_id,
        action="admin_update_user",
        target_type="users",
        target_id=target_id,
        success=True,
        status_code=200,
        details={"changes": changes, "target_user_id": target_id}
    )
    session.commit()

    return {
        "id": target_user.id,
        "username": target_user.username,
        "email": target_user.email,
        "type": target_user.type,
        "is_verified": target_user.is_verified,
        "is_banned": target_user.is_banned,
        "created_at": target_user.created_at,
        "updated_at": target_user.updated_at,
    }


@router.patch("/admin/users/{target_id}", response_model=AdminUserRead, status_code=200)
def admin_update_user(target_id: int, data: AdminUserUpdate, admin_id: int = Depends(require_admin)):
    with Session(engine) as session:
        try:
            return admin_update_user_service(session, target_id, data, admin_id)
        except HTTPException as e:
            session.rollback()
            log_action(
                session=session,
                user_id=admin_id,
                action="admin_update_user",
                target_type="users",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail), "target_user_id": target_id}
            )
            session.commit()
            raise

def admin_delete_user_service(session: Session, target_id: int, admin_id: int):

    target_user = session.exec(
        select(users).where(users.id == target_id)
    ).first()

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_id == admin_id:
        raise HTTPException(status_code=409, detail="You cannot delete your own account via admin panel")

    if target_user.type == "admin":
        raise HTTPException(status_code=409, detail="Cannot delete another admin account")

    info = {
        "id": target_user.id,
        "username": target_user.username,
        "email": target_user.email,
        "type": target_user.type,
    }

    session.delete(target_user)
    session.commit()

    log_action(
        session=session,
        user_id=admin_id,
        action="admin_delete_user",
        target_type="users",
        target_id=target_id,
        success=True,
        status_code=200,
        details={"deleted_user": info}
    )
    session.commit()

    return {
        "deleted": True,
        "user_id": target_id
    }


@router.delete("/admin/users/{target_id}", status_code=200)
def admin_delete_user(target_id: int, admin_id: int = Depends(require_admin)):
    with Session(engine) as session:
        try:
            return admin_delete_user_service(session, target_id, admin_id)
        except HTTPException as e:
            session.rollback()
            log_action(
                session=session,
                user_id=admin_id,
                action="admin_delete_user",
                target_type="users",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail), "target_user_id": target_id}
            )
            session.commit()
            raise

def admin_get_users_service(session: Session, user_type: Optional[str], is_banned: Optional[bool], limit: int, offset: int):

    base_query = select(users)

    if user_type is not None:
        base_query = base_query.where(users.type == user_type)

    if is_banned is not None:
        base_query = base_query.where(users.is_banned == is_banned)

    total = session.exec(
        select(func.count()).select_from(base_query.subquery())
    ).one()

    results = session.exec(
        base_query.offset(offset).limit(limit)
    ).all()

    return {
        "total":  total,
        "limit":  limit,
        "offset": offset,
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "type": u.type,
                "is_verified": u.is_verified,
                "is_banned": u.is_banned,
                "created_at": u.created_at,
                "updated_at": u.updated_at,
            }
            for u in results
        ]
    }


@router.get("/admin/users", response_model=AdminUserListResponse, status_code=200)
def admin_get_users(
    user_type: Optional[str]  = None,
    is_banned: Optional[bool] = None,
    limit: int            = 20,
    offset: int            = 0,
    admin_id: int            = Depends(require_admin)
):
    with Session(engine) as session:
        try:
            return admin_get_users_service(session, user_type, is_banned, limit, offset)
        except HTTPException as e:
            session.rollback()
            log_action(
                session=session,
                user_id=admin_id,
                action="admin_get_users",
                target_type="users",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail)}
            )
            session.commit()
            raise