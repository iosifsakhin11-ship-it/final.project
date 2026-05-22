"""
test_favorites.py — Unit tests for the favorites module.

Covers: add, view, remove, duplicate (409), per-user isolation.
"""

import pytest
from tests.conftest import register_and_verify, do_login

LISTING = {"address": "1 Fav St", "price": 200000, "bedrooms": 2,
           "category": "residential", "amenities": []}


class TestFavorites:
    def _setup_user_and_listing(self, client, db_session,
                                 uname="fuser", email="fuser@test.com"):
        register_and_verify(client, uname, email, "P@ss1")
        token = do_login(client, db_session, email, "P@ss1")
        create = client.post(f"/listings?token={token}", json=LISTING)
        lid = create.json()["id"]
        return token, lid

    def test_add_favorite(self, client, db_session):
        token, lid = self._setup_user_and_listing(client, db_session)
        resp = client.post(f"/favorites?listing_id={lid}&token={token}")
        assert resp.status_code == 201

    def test_view_favorites(self, client, db_session):
        token, lid = self._setup_user_and_listing(client, db_session)
        client.post(f"/favorites?listing_id={lid}&token={token}")
        resp = client.get(f"/favorites?token={token}")
        assert resp.status_code == 200
        assert len(resp.json().get("favorites", [])) >= 1

    def test_remove_favorite(self, client, db_session):
        token, lid = self._setup_user_and_listing(client, db_session)
        client.post(f"/favorites?listing_id={lid}&token={token}")
        resp = client.delete(f"/favorites/{lid}?token={token}")
        assert resp.status_code == 200

    def test_duplicate_favorite_rejected(self, client, db_session):
        token, lid = self._setup_user_and_listing(client, db_session)
        client.post(f"/favorites?listing_id={lid}&token={token}")
        resp = client.post(f"/favorites?listing_id={lid}&token={token}")
        assert resp.status_code == 409

    def test_favorites_isolated_per_user(self, client, db_session):
        token1, lid = self._setup_user_and_listing(client, db_session, "u1", "u1@test.com")
        client.post(f"/favorites?listing_id={lid}&token={token1}")

        register_and_verify(client, "u2", "u2@test.com", "P@ss1")
        token2 = do_login(client, db_session, "u2@test.com", "P@ss1")
        resp = client.get(f"/favorites?token={token2}")
        assert len(resp.json().get("favorites", [])) == 0

    def test_favorite_nonexistent_listing(self, client, db_session):
        register_and_verify(client, "fnl", "fnl@test.com", "P@ss1")
        token = do_login(client, db_session, "fnl@test.com", "P@ss1")
        resp = client.post(f"/favorites?listing_id=99999&token={token}")
        assert resp.status_code in [404, 400, 500]

    def test_remove_nonexistent_favorite(self, client, db_session):
        register_and_verify(client, "rnf", "rnf@test.com", "P@ss1")
        token = do_login(client, db_session, "rnf@test.com", "P@ss1")
        resp = client.delete(f"/favorites/99999?token={token}")
        assert resp.status_code in [404, 400]

    def test_favorite_unauthenticated(self, client):
        resp = client.post("/favorites?listing_id=1")
        assert resp.status_code in [401, 422]
