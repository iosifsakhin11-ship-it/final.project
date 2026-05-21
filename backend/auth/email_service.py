import os
from dotenv import load_dotenv
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from typing import List
import asyncio

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Load mail credentials with safe defaults
_mail_user = os.getenv("MAIL_USERNAME", "")
_mail_pass = os.getenv("MAIL_PASSWORD", "")
_mail_from = os.getenv("MAIL_FROM", _mail_user)
_mail_port = int(os.getenv("MAIL_PORT", "587"))
_mail_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")

# Check if real credentials are configured
_has_real_smtp = bool(_mail_user and _mail_pass
                      and _mail_user != "your@gmail.com"
                      and _mail_pass != "fake"
                      and _mail_pass != "placeholder"
                      and _mail_user != "noreply@example.com")

if _has_real_smtp:
    print(f"[EMAIL] SMTP configured: {_mail_user} via {_mail_server}:{_mail_port}")
    conf = ConnectionConfig(
        MAIL_USERNAME=_mail_user,     # type: ignore
        MAIL_PASSWORD=_mail_pass,     # type: ignore
        MAIL_FROM=_mail_from,         # type: ignore
        MAIL_PORT=_mail_port,
        MAIL_SERVER=_mail_server,     # type: ignore
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
    )
else:
    print(f"[EMAIL] No real SMTP credentials found — emails will be printed to console instead")
    print(f"[EMAIL] To enable real emails, create backend/.env with your Gmail App Password")
    conf = None


def send_email_sync(subject: str, recipients: List[str], body: str):
    """Send an email. Falls back to console output if SMTP is not configured."""

    # If no real SMTP, print the email content to console (useful for demo)
    if not _has_real_smtp or conf is None:
        print("")
        print("=" * 60)
        print(f"  EMAIL (console mode — no SMTP configured)")
        print(f"  To:      {', '.join(recipients)}")
        print(f"  Subject: {subject}")
        print(f"  Body:    {body}")
        print("=" * 60)
        print("")
        return

    # Real SMTP sending
    message = MessageSchema(
        subject=subject,
        recipients=recipients,  # type: ignore
        body=body,
        subtype="plain"         # type: ignore
    )
    fm = FastMail(conf)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(fm.send_message(message))
        finally:
            loop.close()
        print(f"[EMAIL SENT] '{subject}' -> {recipients}")
    except Exception as e:
        # Print the FULL error so you can debug during demo
        print(f"[EMAIL ERROR] Failed to send '{subject}' to {recipients}")
        print(f"[EMAIL ERROR] Reason: {e}")
        print(f"[EMAIL ERROR] Check your .env: MAIL_USERNAME, MAIL_PASSWORD, MAIL_SERVER, MAIL_PORT")

def send_verification_email(email: str, token: str):
    link = f"{BASE_URL}/verify-email?token={token}"
    send_email_sync(
        subject = "Verify your HomeFinder account",
        recipients = [email],
        body = f"Click here to verify your account: {link}\n\nExpires in 24 hours."
    )


def send_otp_email(email: str, otp: str):
    send_email_sync(
        subject = "Your HomeFinder verification code",
        recipients = [email],
        body = f"Your verification code is: {otp}\n\nThis code expires in 30 seconds."
    )


def send_listing_notification_email(email: str, listing_id: int, address: str, category: str, price: float):
    send_email_sync(
        subject = "A new listing matches your preferences",
        recipients = [email],
        body = f"A new {category} listing has been added at {address} for £{price:,.2f}\n\nView it here: {BASE_URL}/listings/{listing_id}"
    )

def send_bid_confirmation_email(email: str, amount: float, address: str, bid_id: int):
    send_email_sync(
        subject    = "Your bid has been submitted - HomeFinder",
        recipients = [email],
        body       = (
            f"Your bid of £{amount:,.2f} on {address} has been received.\n\n"
            f"Bid reference: #{bid_id}\n"
            f"You will be notified when the owner responds.\n\n"
            f"View your bids: {BASE_URL}/bids/me"
        )
    )

def send_bid_accepted_email(email: str, amount: float, address: str, bid_id: int):
    send_email_sync(
        subject    = "Your bid has been accepted! - HomeFinder",
        recipients = [email],
        body       = (
            f"Congratulations! Your bid of £{amount:,.2f} on {address} has been accepted.\n\n"
            f"Bid reference: #{bid_id}\n"
            f"The listing owner will be in touch to proceed.\n\n"
            f"View your bid: {BASE_URL}/bids/{bid_id}"
        )
    )

def send_bid_rejected_email(email: str, amount: float, address: str, bid_id: int):
    send_email_sync(
        subject    = "Update on your bid - HomeFinder",
        recipients = [email],
        body       = (
            f"Unfortunately your bid of £{amount:,.2f} on {address} has been rejected.\n\n"
            f"Bid reference: #{bid_id}\n"
            f"You can place a new bid or browse similar listings: {BASE_URL}/listings"
        )
    )

def send_bid_cancelled_email(email: str, amount: float, address: str, bid_id: int):
    send_email_sync(
        subject    = "Bid cancelled - HomeFinder",
        recipients = [email],
        body       = (
            f"Your bid of £{amount:,.2f} on {address} has been cancelled.\n\n"
            f"Bid reference: #{bid_id}\n"
            f"Browse similar listings: {BASE_URL}/listings"
        )
    )

def send_bid_auto_rejected_email(email: str, amount: float, address: str, bid_id: int):
    send_email_sync(
        subject    = "Update on your bid - HomeFinder",
        recipients = [email],
        body       = (
            f"Your bid of £{amount:,.2f} on {address} has been rejected as another offer has been accepted.\n\n"
            f"Bid reference: #{bid_id}\n"
            f"Browse similar listings: {BASE_URL}/listings"
        )
    )

def send_viewing_confirmation_email(email: str, address: str, viewing_at: str, viewing_id: int):
    send_email_sync(
        subject    = "Viewing request received - HomeFinder",
        recipients = [email],
        body       = (
            f"Your viewing request for {address} on {viewing_at} has been received.\n\n"
            f"Viewing reference: #{viewing_id}\n"
            f"You will be notified when the owner confirms.\n\n"
            f"View your viewings: {BASE_URL}/viewings/me"
        )
    )

def send_viewing_accepted_email(email: str, address: str, viewing_at: str, viewing_id: int):
    send_email_sync(
        subject    = "Viewing confirmed! - HomeFinder",
        recipients = [email],
        body       = (
            f"Your viewing at {address} on {viewing_at} has been confirmed.\n\n"
            f"Viewing reference: #{viewing_id}\n"
            f"Please arrive on time. Contact the owner via chat if you need to reschedule.\n\n"
            f"View your viewings: {BASE_URL}/viewings/me"
        )
    )

def send_viewing_rejected_email(email: str, address: str, viewing_at: str, viewing_id: int):
    send_email_sync(
        subject    = "Viewing request update - HomeFinder",
        recipients = [email],
        body       = (
            f"Unfortunately your viewing request for {address} on {viewing_at} has been rejected.\n\n"
            f"Viewing reference: #{viewing_id}\n"
            f"You can request a different time or browse similar listings: {BASE_URL}/listings"
        )
    )

def send_viewing_cancelled_email(email: str, address: str, viewing_at: str, viewing_id: int):
    send_email_sync(
        subject    = "Viewing cancelled - HomeFinder",
        recipients = [email],
        body       = (
            f"Your viewing at {address} on {viewing_at} has been cancelled.\n\n"
            f"Viewing reference: #{viewing_id}\n"
            f"Browse similar listings: {BASE_URL}/listings"
        )
    )

def send_viewing_auto_cancelled_email(email: str, address: str, viewing_at: str, viewing_id: int):
    send_email_sync(
        subject    = "Viewing cancelled - HomeFinder",
        recipients = [email],
        body       = (
            f"Your viewing at {address} on {viewing_at} has been cancelled as the listing has been accepted by another buyer.\n\n"
            f"Viewing reference: #{viewing_id}\n"
            f"Browse similar listings: {BASE_URL}/listings"
        )
    )

def send_inquiry_confirmation_email(email: str, address: str):
    send_email_sync(
        subject    = "Inquiry sent - HomeFinder",
        recipients = [email],
        body       = (
            f"Your inquiry about {address} has been sent.\n\n"
            f"The owner will respond via your chat thread.\n\n"
            f"View your chats: {BASE_URL}/chats"
        )
    )