"""
test_unit_auth.py — Unit tests for the auth module.

Covers: registration, email verification, resend, login factor-1,
OTP factor-2, profile retrieval, profile update, password change, logout.
"""

import pytest
from tests.conftest import register_and_verify, do_login


class TestRegistration:
    def test_register_success(self, client):
        resp = client.post("/users", json={"username": "u1", "email": "u1@test.com", "password": "P@ss1"})
        assert resp.status_code == 201
        assert resp.json()["is_verified"] is False

    def test_register_duplicate_email(self, client):
        client.post("/users", json={"username": "u1", "email": "dup@test.com", "password": "P@ss1"})
        resp = client.post("/users", json={"username": "u2", "email": "dup@test.com", "password": "P@ss1"})
        assert resp.status_code == 400

    def test_register_duplicate_username(self, client):
        client.post("/users", json={"username": "same", "email": "a@test.com", "password": "P@ss1"})
        resp = client.post("/users", json={"username": "same", "email": "b@test.com", "password": "P@ss1"})
        assert resp.status_code == 400

    def test_register_creates_verification_token(self, client, db_session):
        client.post("/users", json={"username": "vt", "email": "vt@test.com", "password": "P@ss1"})
        from auth.email_verification_model import email_verifications
        from sqlmodel import select
        rows = db_session.exec(select(email_verifications)).all()
        assert len(rows) >= 1


class TestEmailVerification:
    def test_verify_valid_token(self, client, db_session):
        client.post("/users", json={"username": "ev", "email": "ev@test.com", "password": "P@ss1"})
        from auth.email_verification_model import email_verifications
        from sqlmodel import select
        tok = db_session.exec(select(email_verifications)).first()
        resp = client.get(f"/verify-email?token={tok.token}")
        assert resp.status_code == 200

    def test_verify_invalid_token(self, client):
        resp = client.get("/verify-email?token=invalid_token_value")
        assert resp.status_code == 404

    def test_resend_verification(self, client):
        client.post("/users", json={"username": "rs", "email": "rs@test.com", "password": "P@ss1"})
        resp = client.post("/resend-verification?email=rs@test.com")
        assert resp.status_code == 200


class TestLoginFactor1:
    def test_login_sends_otp(self, client, db_session):
        register_and_verify(client, "lf1", "lf1@test.com", "P@ss1")
        resp = client.post("/login", json={"email": "lf1@test.com", "password": "P@ss1"})
        assert resp.status_code == 200
        assert "code sent" in resp.json()["message"].lower() or "verification" in resp.json()["message"].lower()

    def test_login_wrong_password(self, client):
        register_and_verify(client, "wp", "wp@test.com", "Correct1")
        resp = client.post("/login", json={"email": "wp@test.com", "password": "Wrong1"})
        assert resp.status_code == 401

    def test_login_unverified_rejected(self, client):
        client.post("/users", json={"username": "uv", "email": "uv@test.com", "password": "P@ss1"})
        resp = client.post("/login", json={"email": "uv@test.com", "password": "P@ss1"})
        assert resp.status_code == 403

    def test_login_nonexistent_email(self, client):
        resp = client.post("/login", json={"email": "none@test.com", "password": "P@ss1"})
        assert resp.status_code == 401


class TestOTPFactor2:
    def test_verify_otp_success(self, client, db_session):
        register_and_verify(client, "otp1", "otp1@test.com", "P@ss1")
        token = do_login(client, db_session, "otp1@test.com", "P@ss1")
        assert token is not None
        assert len(token) == 64

    def test_verify_otp_invalid_code(self, client, db_session):
        register_and_verify(client, "otp2", "otp2@test.com", "P@ss1")
        client.post("/login", json={"email": "otp2@test.com", "password": "P@ss1"})
        resp = client.post("/verify-otp", json={"email": "otp2@test.com", "otp": "000000"})
        assert resp.status_code == 401

    def test_otp_revokes_prior_sessions(self, client, db_session):
        register_and_verify(client, "rev", "rev@test.com", "P@ss1")
        token1 = do_login(client, db_session, "rev@test.com", "P@ss1")
        token2 = do_login(client, db_session, "rev@test.com", "P@ss1")
        # old token should be revoked
        resp = client.get(f"/users/me?token={token1}")
        assert resp.status_code == 401
        resp = client.get(f"/users/me?token={token2}")
        assert resp.status_code == 200


class TestProfile:
    def test_get_me(self, client, db_session):
        register_and_verify(client, "me", "me@test.com", "P@ss1")
        token = do_login(client, db_session, "me@test.com", "P@ss1")
        resp = client.get(f"/users/me?token={token}")
        assert resp.status_code == 200
        assert resp.json()["email"] == "me@test.com"

    def test_get_me_no_token(self, client):
        resp = client.get("/users/me")
        assert resp.status_code in [401, 422]


class TestLogout:
    def test_logout_revokes_session(self, client, db_session):
        register_and_verify(client, "lo", "lo@test.com", "P@ss1")
        token = do_login(client, db_session, "lo@test.com", "P@ss1")
        resp = client.post(f"/logout?token={token}")
        assert resp.status_code == 200
        resp = client.get(f"/users/me?token={token}")
        assert resp.status_code == 401

    def test_logout_invalid_token(self, client):
        resp = client.post("/logout?token=invalidtokenthatdoesnotexist")
        assert resp.status_code == 401

    def test_double_logout(self, client, db_session):
        register_and_verify(client, "dl", "dl@test.com", "P@ss1")
        token = do_login(client, db_session, "dl@test.com", "P@ss1")
        client.post(f"/logout?token={token}")
        resp = client.post(f"/logout?token={token}")
        assert resp.status_code == 401


class TestPasswordChange:
    def test_change_password_success(self, client, db_session):
        register_and_verify(client, "cp", "cp@test.com", "OldPass1")
        token = do_login(client, db_session, "cp@test.com", "OldPass1")
        resp = client.post(f"/users/me/change-password?token={token}",
                           json={"current_password": "OldPass1", "new_password": "NewPass2"})
        assert resp.status_code == 200

    def test_change_password_wrong_current(self, client, db_session):
        register_and_verify(client, "cpw", "cpw@test.com", "RealPass1")
        token = do_login(client, db_session, "cpw@test.com", "RealPass1")
        resp = client.post(f"/users/me/change-password?token={token}",
                           json={"current_password": "WrongPass", "new_password": "NewPass2"})
        assert resp.status_code in [400, 401, 403]


class TestProfileUpdate:
    def test_update_username(self, client, db_session):
        register_and_verify(client, "upd", "upd@test.com", "P@ss1")
        token = do_login(client, db_session, "upd@test.com", "P@ss1")
        resp = client.patch(f"/users/me?token={token}", json={"username": "newname"})
        assert resp.status_code == 200
