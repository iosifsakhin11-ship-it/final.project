from typing import Optional, Dict, Any
from sqlmodel import Session
from datetime import datetime

from server import engine
from .audit_logs_model import AuditLog

def log_action(
    session: Session,
    user_id: Optional[int],
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    success: bool = True,
    status_code: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
):

    log = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        success=success,
        status_code=status_code,
        details=details,
    )
    session.add(log)