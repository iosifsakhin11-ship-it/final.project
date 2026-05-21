import bcrypt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from config.config import ENCODER
from config.rate_limit import check_rate_limit
from server import engine
from .user_model import userRead
from .user_model import users as user
from audit.audit import log_action
from .email_service import send_verification_email
import hashlib
import secrets
import re
from datetime import datetime, timezone, timedelta
from .email_verification_model import email_verifications

router = APIRouter()

class userCreate(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    email: str = Field(max_length=100)
    password: str = Field(min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email format")
        return v.lower().strip()

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username must contain only letters, numbers, and underscores")
        return v.strip()

def generate_verification_token() -> str:
    return hashlib.sha256(secrets.token_bytes(32)).hexdigest()

@router.post("/users", response_model=userRead, status_code=201)
def create_user(data: userCreate, request: Request):
    check_rate_limit(request, limit=3, window=60)  # 3 registrations per minute

    #hashing password
    hashed = bcrypt.hashpw(data.password.encode(ENCODER), bcrypt.gensalt())

    #appending db
    with Session(engine) as session:
        new_user = user(
            username=data.username,
            email=data.email,
            password_hash=hashed.decode(ENCODER),
            is_verified=False
        )
        session.add(new_user)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()

            log_action(
                session=session,
                user_id = None,
                action="create_user",
                target_type="users",
                success=False,
                status_code=400,
                details={"error": "IntegrityError"}
            )
            session.commit()

            raise HTTPException(status_code=400, detail="Username or email already exist")
        session.refresh(new_user)

        token = generate_verification_token()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        verification = email_verifications(
            user_id=new_user.id, # type: ignore
            token=token,
            expires_at=expires_at
        )
        session.add(verification)
        session.commit()

        send_verification_email(new_user.email, token)
        
        log_action(
            session=session,
            user_id=new_user.id,
            action="create_user",
            target_type="users",
            target_id=new_user.id,
            success=True,
            status_code=201,
            details={
                "username": data.username,
                "email": data.email
            }
        )
        session.commit()

        return userRead(
            id=new_user.id, # type: ignore
            username=new_user.username,
            email=new_user.email,
            type=new_user.type,
            created_at=new_user.created_at,
            updated_at=new_user.updated_at,
            is_verified=new_user.is_verified
        )
    
@router.get("/verify-email", status_code=200)
def verify_email(token: str):
    with Session(engine) as session:

        verification = session.exec(
            select(email_verifications).where(
                email_verifications.token == token,
                email_verifications.used_at == None
            )
        ).first()

        if not verification:
            raise HTTPException(status_code=404, detail="Invalid or already used verification token")

        if verification.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Verification token has expired")

        verification.used_at = datetime.now(timezone.utc)
        session.add(verification)

        user_obj = session.exec(
            select(user).where(user.id == verification.user_id)
        ).first()

        if not user_obj:
            raise HTTPException(status_code=404, detail="User not found")

        user_obj.is_verified = True
        session.add(user_obj)
        session.commit()

        log_action(
            session=session,
            user_id=user_obj.id,
            action="verify_email",
            target_type="users",
            target_id=user_obj.id,
            success=True,
            status_code=200,
            details={"email": user_obj.email}
        )
        session.commit()

        return {"message": "Email verified successfully"}


@router.post("/resend-verification", status_code=200)
def resend_verification(email: str):
    with Session(engine) as session:

        user_obj = session.exec(
            select(user).where(user.email == email)
        ).first()

        if not user_obj:
            raise HTTPException(status_code=404, detail="User not found")

        if user_obj.is_verified:
            raise HTTPException(status_code=409, detail="Email is already verified")

        old_tokens = session.exec(
            select(email_verifications).where(
                email_verifications.user_id == user_obj.id,
                email_verifications.used_at == None
            )
        ).all()

        for old_token in old_tokens:
            old_token.used_at = datetime.now(timezone.utc)
            session.add(old_token)

        token = generate_verification_token()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        new_verification = email_verifications(
            user_id=user_obj.id, # type: ignore
            token=token,
            expires_at=expires_at
        )
        session.add(new_verification)
        session.commit()

        send_verification_email(user_obj.email, token)

        log_action(
            session=session,
            user_id=user_obj.id,
            action="resend_verification",
            target_type="users",
            target_id=user_obj.id,
            success=True,
            status_code=200,
            details={"email": email}
        )
        session.commit()

        return {"message": "Verification email resent"}