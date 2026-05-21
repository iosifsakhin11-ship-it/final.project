import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from config.config import ENCODER, SESSION_DURATION_DAYS
from config.rate_limit import check_rate_limit
from server import engine
from .hash_token import hash_token
from .user_model import user_sessions as session_model
from .user_model import users as user
from .user_model import LoginResponse, userRead
from audit.audit import log_action
import random
from .email_service import send_otp_email
from .twoFA_model import two_factor_tokens
from .user_model import OTPRequest, OTPVerify, OTPResponse
from .dependencies import is_banned

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

#generate tokens for sessions
def generate_token():
    raw_token = secrets.token_hex(32)
    return raw_token, hash_token(raw_token)

def generate_otp() -> str:
    return str(random.randint(100000, 999999))

@router.post("/login", status_code=200, response_model=OTPResponse)
def login(data: LoginRequest, request: Request):
    check_rate_limit(request, limit=5, window=60)  # 5 login attempts per minute
    with Session(engine) as session:
        statement = select(user).where(user.email == data.email)
        user_obj = session.exec(statement).first()

        # if sql query is not found or if password verification returns false rasie a error"
        if not (user_obj and bcrypt.checkpw(data.password.encode(ENCODER), user_obj.password_hash.encode(ENCODER))):
            log_action(
                session=session,
                user_id=None,
                action="login_failed",
                target_type="users",
                success=False,
                status_code=401,
                details={
                    "email": data.email,
                    "reason": "invalid_credentials"
                }
            )
            session.commit()

            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        is_banned(user_obj)

        if not user_obj.is_verified:
            raise HTTPException(status_code=403, detail="Please verify your email before logging in")

        old_otps = session.exec(
            select(two_factor_tokens).where(
                two_factor_tokens.user_id == user_obj.id,
                two_factor_tokens.used_at == None
            )
        ).all()
        for old_otp in old_otps:
            old_otp.used_at = datetime.now(timezone.utc)
            session.add(old_otp)

        otp = generate_otp()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)

        new_otp = two_factor_tokens(
            user_id=user_obj.id, # type: ignore
            otp=otp,
            expires_at=expires_at
        )
        session.add(new_otp)
        session.commit()

        send_otp_email(user_obj.email, otp)

        log_action(
            session=session,
            user_id=user_obj.id,
            action="otp_sent",
            target_type="users",
            target_id=user_obj.id,
            success=True,
            status_code=200,
            details={"email": data.email}
        )
        session.commit()

        return OTPResponse(message="Verification code sent to your email")

@router.post("/verify-otp", response_model=LoginResponse, status_code=200)
def verify_otp(data: OTPVerify, request: Request):
    check_rate_limit(request, limit=10, window=60)  # 10 OTP attempts per minute
    with Session(engine) as session:

        user_obj = session.exec(
            select(user).where(user.email == data.email)
        ).first()

        if not user_obj:
            raise HTTPException(status_code=404, detail="User not found")

        # find valid OTP
        otp_obj = session.exec(
            select(two_factor_tokens).where(
                two_factor_tokens.user_id == user_obj.id,
                two_factor_tokens.otp == data.otp,
                two_factor_tokens.used_at == None
            )
        ).first()

        if not otp_obj:
            log_action(
                session=session,
                user_id=user_obj.id,
                action="otp_failed",
                target_type="users",
                success=False,
                status_code=401,
                details={"reason": "invalid_otp"}
            )
            session.commit()
            raise HTTPException(status_code=401, detail="Invalid verification code")

        # check expiry
        if otp_obj.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            log_action(
                session=session,
                user_id=user_obj.id,
                action="otp_failed",
                target_type="users",
                success=False,
                status_code=401,
                details={"reason": "otp_expired"}
            )
            session.commit()
            raise HTTPException(status_code=401, detail="Verification code has expired — please login again")

        # mark OTP as used
        otp_obj.used_at = datetime.now(timezone.utc)
        session.add(otp_obj)

        # revoke previous sessions
        active_sessions = session.exec(
            select(session_model).where(
                session_model.user_id   == user_obj.id,
                session_model.revoked_at == None
            )
        ).all()
        for s in active_sessions:
            s.revoked_at = datetime.now(timezone.utc)
            session.add(s)

        # create new session
        raw_token, token_hash = generate_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_DURATION_DAYS)

        new_session = session_model(
            user_id=user_obj.id, # type: ignore
            token=token_hash,
            expires_at=expires_at
        )
        session.add(new_session)
        session.commit()
        session.refresh(new_session)

        log_action(
            session=session,
            user_id=user_obj.id,
            action="login_success",
            target_type="users",
            target_id=user_obj.id,
            success=True,
            status_code=200,
            details={
                "session_created": True,
                "active_sessions_revoked": len(active_sessions)
            }
        )
        session.commit()

        return LoginResponse(
            message=f"Welcome, {user_obj.username}",
            token=raw_token,
            user=userRead(
                id=user_obj.id,  # type: ignore
                username=user_obj.username,
                email=user_obj.email,
                type=user_obj.type,
                created_at=user_obj.created_at,
                updated_at=user_obj.updated_at,
                is_verified=user_obj.is_verified
            )
        )