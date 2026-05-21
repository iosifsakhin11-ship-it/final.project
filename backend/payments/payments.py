from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from server import engine
from auth.dependencies import get_current_user_id
from admin.dependencies import require_admin
from audit.audit import log_action
from .payments_model import payment_records, PaymentStatus, PaymentOut, PaymentListOut, AdminPaymentStatusUpdate

router = APIRouter()


def create_payment_record(session: Session, user_id: int, bid_id: int, amount: float, payment_method: str):
    new_payment = payment_records(
        user_id=user_id,
        bid_id=bid_id,
        amount=amount, # type: ignore
        payment_method=payment_method,
        status=PaymentStatus.pending
    )
    session.add(new_payment)
    session.flush()

    log_action(
        session=session,
        user_id=user_id,
        action="create_payment_record",
        target_type="payment_records",
        target_id=new_payment.id,
        success=True,
        status_code=201,
        details={
            "bid_id": bid_id,
            "amount": str(amount),
            "payment_method": payment_method
        }
    )

    return new_payment


def get_my_payments_service(session: Session, user_id: int):
    my_payments = session.exec(
        select(payment_records).where(payment_records.user_id == user_id)
    ).all()

    return {
        "payments": [
            {
                "id": p.id,
                "user_id": p.user_id,
                "bid_id": p.bid_id,
                "amount": p.amount,
                "payment_method": p.payment_method,
                "status": p.status,
                "reference": p.reference,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            }
            for p in my_payments
        ],
        "total": len(my_payments)
    }


def get_payment_service(session: Session, payment_id: int, user_id: int):
    payment = session.exec(
        select(payment_records).where(payment_records.id == payment_id)
    ).first()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    # only the user or admin can view a payment
    if payment.user_id != user_id:
        raise HTTPException(status_code=403, detail="You do not have permission to view this payment")

    return {
        "id": payment.id,
        "user_id": payment.user_id,
        "bid_id": payment.bid_id,
        "amount": payment.amount,
        "payment_method": payment.payment_method,
        "status": payment.status,
        "reference": payment.reference,
        "created_at": payment.created_at,
        "updated_at": payment.updated_at,
    }


def admin_update_payment_service(session: Session, payment_id: int, data: AdminPaymentStatusUpdate, admin_id: int):
    payment = session.exec(
        select(payment_records).where(payment_records.id == payment_id)
    ).first()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    old_status = payment.status

    payment.status = data.status
    if data.reference is not None:
        payment.reference = data.reference

    session.add(payment)
    session.commit()
    session.refresh(payment)

    log_action(
        session=session,
        user_id=admin_id,
        action="admin_update_payment",
        target_type="payment_records",
        target_id=payment_id,
        success=True,
        status_code=200,
        details={
            "old_status": old_status,
            "new_status": data.status,
            "reference": data.reference
        }
    )
    session.commit()

    return {
        "id": payment.id,
        "user_id": payment.user_id,
        "bid_id": payment.bid_id,
        "amount": payment.amount,
        "payment_method": payment.payment_method,
        "status": payment.status,
        "reference": payment.reference,
        "created_at": payment.created_at,
        "updated_at": payment.updated_at,
    }


def admin_get_payments_service(session: Session, status: str | None, limit: int, offset: int):
    base_query = select(payment_records)

    if status is not None:
        base_query = base_query.where(payment_records.status == status)

    total = session.exec(
        select(func.count()).select_from(base_query.subquery())
    ).one()

    results = session.exec(
        base_query.offset(offset).limit(limit)
    ).all()

    return {
        "payments": [
            {
                "id": p.id,
                "user_id": p.user_id,
                "bid_id": p.bid_id,
                "amount": p.amount,
                "payment_method": p.payment_method,
                "status": p.status,
                "reference": p.reference,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            }
            for p in results
        ],
        "total": total
    }


@router.get("/payments/me", response_model=PaymentListOut)
def get_my_payments(user_id: int = Depends(get_current_user_id)):
    with Session(engine) as session:
        return get_my_payments_service(session, user_id)


@router.get("/payments/{payment_id}", response_model=PaymentOut)
def get_payment(payment_id: int, user_id: int = Depends(get_current_user_id)):
    with Session(engine) as session:
        try:
            return get_payment_service(session, payment_id, user_id)
        except HTTPException as e:
            log_action(
                session=session,
                user_id=user_id,
                action="get_payment",
                target_type="payment_records",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail), "payment_id": payment_id}
            )
            session.commit()
            raise


@router.patch("/admin/payments/{payment_id}", response_model=PaymentOut)
def admin_update_payment(payment_id: int, data: AdminPaymentStatusUpdate, admin_id: int = Depends(require_admin)):
    with Session(engine) as session:
        try:
            return admin_update_payment_service(session, payment_id, data, admin_id)
        except HTTPException as e:
            session.rollback()
            log_action(
                session=session,
                user_id=admin_id,
                action="admin_update_payment",
                target_type="payment_records",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail), "payment_id": payment_id}
            )
            session.commit()
            raise


@router.get("/admin/payments", response_model=PaymentListOut)
def admin_get_payments(
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    admin_id: int = Depends(require_admin)
):
    with Session(engine) as session:
        try:
            return admin_get_payments_service(session, status, limit, offset)
        except HTTPException as e:
            log_action(
                session=session,
                user_id=admin_id,
                action="admin_get_payments",
                target_type="payment_records",
                success=False,
                status_code=e.status_code,
                details={"error": str(e.detail)}
            )
            session.commit()
            raise