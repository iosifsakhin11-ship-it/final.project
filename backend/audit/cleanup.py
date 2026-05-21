from datetime import datetime, timezone, timedelta
from sqlmodel import Session, select, delete, col
from server import engine
from .audit_logs_model import AuditLog

def cleanup_old_logs():
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)  # 3 months
    
    with Session(engine) as session:
        result = session.exec(
            delete(AuditLog).where(col(AuditLog.created_at) < cutoff)
        )
        deleted_count = result.rowcount
        session.commit()
        print(f"Audit cleanup: deleted {deleted_count} logs older than {cutoff}")