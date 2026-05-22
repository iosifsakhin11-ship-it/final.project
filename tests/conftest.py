"""
conftest.py — Shared pytest fixtures for HomeFinder test suite.

Provides:
  - TestClient against the real FastAPI app
  - Isolated test database (user_auth_test) with per-test truncation
  - register_and_verify() — creates a verified user
  - do_login() — drives the full 2FA flow and returns a session token
  - SMTP is fully mocked (no real emails sent)
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, text

# Env must be set before importing app modules
os.environ["DATABASE_URL"] = "mysql+pymysql://root:@localhost:3306/user_auth_test"
os.environ["BASE_URL"] = "http://localhost:8000"
os.environ["MAIL_USERNAME"] = "test@test.com"
os.environ["MAIL_PASSWORD"] = "fake"
os.environ["MAIL_FROM"] = "test@test.com"
os.environ["MAIL_PORT"] = "587"
os.environ["MAIL_SERVER"] = "smtp.gmail.com"


@pytest.fixture(autouse=True)
def mock_email():
    """Mock all email sending so no real SMTP calls are made."""
    with patch("auth.email_service.send_verification_email", return_value=None), \
         patch("auth.email_service.send_otp_email", return_value=None), \
         patch("auth.email_service.send_confirmation_email", return_value=None):
        yield


@pytest.fixture(scope="session")
def engine():
    from server import engine as app_engine
    SQLModel.metadata.create_all(app_engine)
    return app_engine


@pytest.fixture(autouse=True)
def truncate_tables(engine):
    """Truncate all tables before each test for hermetic isolation."""
    with Session(engine) as session:
        session.exec(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in reversed(SQLModel.metadata.sorted_tables):
            session.exec(text(f"TRUNCATE TABLE `{table.name}`"))
        session.exec(text("SET FOREIGN_KEY_CHECKS = 1"))
        session.commit()


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


@pytest.fixture
def db_session(engine):
    with Session(engine) as session:
        yield session


def register_and_verify(client, username="testuser", email="test@example.com", password="Pass123!"):
    """Register a user and immediately verify their email in the DB."""
    resp = client.post("/users", json={"username": username, "email": email, "password": password})
    assert resp.status_code == 201, resp.text
    user_data = resp.json()

    # Directly verify in DB (bypass email link)
    from server import engine
    with Session(engine) as session:
        from auth.user_model import users
        from sqlmodel import select
        u = session.exec(select(users).where(users.email == email)).first()
        u.is_verified = True
        session.add(u)
        session.commit()

    return user_data


def do_login(client, db_session, email="test@example.com", password="Pass123!"):
    """Drive the full 2FA login flow: POST /login -> fetch OTP from DB -> POST /verify-otp."""
    resp = client.post("/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text

    # Fetch OTP directly from DB
    from auth.twoFA_model import two_factor_tokens
    from sqlmodel import select
    otp_row = db_session.exec(
        select(two_factor_tokens).where(
            two_factor_tokens.used_at == None
        ).order_by(two_factor_tokens.id.desc())
    ).first()
    assert otp_row is not None, "No OTP found in DB"

    resp = client.post("/verify-otp", json={"email": email, "otp": otp_row.otp})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return data["token"]
