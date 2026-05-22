"""
test_chats.py — Unit and integration tests for chats, bids, and viewings.

Covers: message sending, bid lifecycle (create/respond/cancel),
viewing lifecycle (create/respond/cancel), owner-only responses,
duplicate guards, self-bid prevention, status transition guards.
"""

import pytest
from tests.conftest import register_and_verify, do_login

LISTING = {"address": "55 Chat Ave", "price": 300000, "bedrooms": 3,
           "category": "residential", "amenities": []}


def setup_owner_and_buyer(client, db_session):
    """Helper: create owner with listing + buyer, return tokens and listing id."""
    register_and_verify(client, "owner", "owner@t.com", "P@ss1")
    t_own = do_login(client, db_session, "owner@t.com", "P@ss1")
    lid = client.post(f"/listings?token={t_own}", json=LISTING).json()["id"]
    register_and_verify(client, "buyer", "buyer@t.com", "P@ss1")
    t_buy = do_login(client, db_session, "buyer@t.com", "P@ss1")
    return t_own, t_buy, lid


# ── Messages ─────────────────────────────────────────────────────────

class TestMessages:
    def test_send_message_creates_chat(self, client, db_session):
        t_own, t_buy, lid = setup_owner_and_buyer(client, db_session)
        resp = client.post(f"/messages?token={t_buy}",
                           json={"listing_id": lid, "content": "Is this available?"})
        assert resp.status_code == 201

    def test_get_chats_returns_threads(self, client, db_session):
        t_own, t_buy, lid = setup_owner_and_buyer(client, db_session)
        client.post(f"/messages?token={t_buy}",
                    json={"listing_id": lid, "content": "Hello"})
        resp = client.get(f"/chats?token={t_buy}")
        assert resp.status_code == 200
        assert len(resp.json().get("chats", [])) >= 1

    def test_get_chat_details(self, client, db_session):
        t_own, t_buy, lid = setup_owner_and_buyer(client, db_session)
        client.post(f"/messages?token={t_buy}",
                    json={"listing_id": lid, "content": "Details please"})
        chats = client.get(f"/chats?token={t_buy}").json()
        chat_id = chats["chats"][0]["id"]
        resp = client.get(f"/chats/{chat_id}?token={t_buy}")
        assert resp.status_code == 200

    def test_cannot_message_own_listing(self, client, db_session):
        register_and_verify(client, "self", "self@t.com", "P@ss1")
        t = do_login(client, db_session, "self@t.com", "P@ss1")
        lid = client.post(f"/listings?token={t}", json=LISTING).json()["id"]
        resp = client.post(f"/messages?token={t}",
                           json={"listing_id": lid, "content": "Test"})
        assert resp.status_code == 409

    def test_message_unauthenticated(self, client):
        resp = client.post("/messages", json={"listing_id": 1, "content": "Hi"})
        assert resp.status_code in [401, 422]


# ── Bids ─────────────────────────────────────────────────────────────

class TestBidCreate:
    def test_create_bid_success(self, client, db_session):
        t_own, t_buy, lid = setup_owner_and_buyer(client, db_session)
        resp = client.post(f"/bids?token={t_buy}",
                           json={"listing_id": lid, "amount": 350000})
        assert resp.status_code == 201
        assert resp.json()["status"] == "pending"

    def test_cannot_bid_on_own_listing(self, client, db_session):
        register_and_verify(client, "own", "own@t.com", "P@ss1")
        t = do_login(client, db_session, "own@t.com", "P@ss1")
        lid = client.post(f"/listings?token={t}", json=LISTING).json()["id"]
        resp = client.post(f"/bids?token={t}",
                           json={"listing_id": lid, "amount": 100})
        assert resp.status_code == 409

    def test_duplicate_pending_bid_rejected(self, client, db_session):
        t_own, t_buy, lid = setup_owner_and_buyer(client, db_session)
        client.post(f"/bids?token={t_buy}",
                    json={"listing_id": lid, "amount": 350000})
        resp = client.post(f"/bids?token={t_buy}",
                           json={"listing_id": lid, "amount": 360000})
        assert resp.status_code == 409

    def test_bid_unauthenticated(self, client):
        resp = client.post("/bids", json={"listing_id": 1, "amount": 100})
        assert resp.status_code in [401, 422]

    def test_get_my_bids(self, client, db_session):
        t_own, t_buy, lid = setup_owner_and_buyer(client, db_session)
        client.post(f"/bids?token={t_buy}",
                    json={"listing_id": lid, "amount": 350000})
        resp = client.get(f"/bids/me?token={t_buy}")
        assert resp.status_code == 200
        assert len(resp.json().get("bids", [])) >= 1

    def test_get_listing_bids_owner_only(self, client, db_session):
        t_own, t_buy, lid = setup_owner_and_buyer(client, db_session)
        client.post(f"/bids?token={t_buy}",
                    json={"listing_id": lid, "amount": 350000})
        resp = client.get(f"/listings/{lid}/bids?token={t_own}")
        assert resp.status_code == 200


class TestBidRespond:
    def test_owner_accepts_bid(self, client, db_session):
        t_own, t_buy, lid = setup_owner_and_buyer(client, db_session)
        bid_id = client.post(f"/bids?token={t_buy}",
                             json={"listing_id": lid, "amount": 350000}).json()["id"]
        resp = client.patch(f"/bids/{bid_id}/respond?token={t_own}",
                            json={"action": "accept"})
        assert resp.status_code == 200

    def test_accept_sets_listing_sold(self, client, db_session):
        t_own, t_buy, lid = setup_owner_and_buyer(client, db_session)
        bid_id = client.post(f"/bids?token={t_buy}",
                             json={"listing_id": lid, "amount": 350000}).json()["id"]
        client.patch(f"/bids/{bid_id}/respond?token={t_own}",
                     json={"action": "accept"})
        detail = client.get(f"/listings/{lid}").json()
        assert detail["status"] == "sold"

    def test_owner_rejects_bid(self, client, db_session):
        t_own, t_buy, lid = setup_owner_and_buyer(client, db_session)
        bid_id = client.post(f"/bids?token={t_buy}",
                             json={"listing_id": lid, "amount": 350000}).json()["id"]
        resp = client.patch(f"/bids/{bid_id}/respond?token={t_own}",
                            json={"action": "reject"})
        assert resp.status_code == 200

    def test_non_owner_cannot_respond(self, client, db_session):
        t_own, t_buy, lid = setup_owner_and_buyer(client, db_session)
        bid_id = client.post(f"/bids?token={t_buy}",
                             json={"listing_id": lid, "amount": 350000}).json()["id"]
        resp = client.patch(f"/bids/{bid_id}/respond?token={t_buy}",
                            json={"action": "accept"})
        assert resp.status_code in [403, 409]

    def test_cannot_respond_to_already_accepted(self, client, db_session):
        t_own, t_buy, lid = setup_owner_and_buyer(client, db_session)
        bid_id = client.post(f"/bids?token={t_buy}",
                             json={"listing_id": lid, "amount": 350000}).json()["id"]
        client.patch(f"/bids/{bid_id}/respond?token={t_own}",
                     json={"action": "accept"})
        resp = client.patch(f"/bids/{bid_id}/respond?token={t_own}",
                            json={"action": "reject"})
        assert resp.status_code == 409


class TestBidCancel:
    def test_bidder_cancels_own_bid(self, client, db_session):
        t_own, t_buy, lid = setup_owner_and_buyer(client, db_session)
        bid_id = client.post(f"/bids?token={t_buy}",
                             json={"listing_id": lid, "amount": 350000}).json()["id"]
        resp = client.patch(f"/bids/{bid_id}/cancel?token={t_buy}")
        assert resp.status_code == 200

    def test_owner_cannot_cancel_buyer_bid(self, client, db_session):
        t_own, t_buy, lid = setup_owner_and_buyer(client, db_session)
        bid_id = client.post(f"/bids?token={t_buy}",
                             json={"listing_id": lid, "amount": 350000}).json()["id"]
        resp = client.patch(f"/bids/{bid_id}/cancel?token={t_own}")
        assert resp.status_code == 403

    def test_cannot_cancel_already_cancelled(self, client, db_session):
        t_own, t_buy, lid = setup_owner_and_buyer(client, db_session)
        bid_id = client.post(f"/bids?token={t_buy}",
                             json={"listing_id": lid, "amount": 350000}).json()["id"]
        client.patch(f"/bids/{bid_id}/cancel?token={t_buy}")
        resp = client.patch(f"/bids/{bid_id}/cancel?token={t_buy}")
        assert resp.status_code == 409


# ── Viewings ─────────────────────────────────────────────────────────

class TestViewingCreate:
    def test_request_viewing_success(self, client, db_session):
        t_own, t_buy, lid = setup_owner_and_buyer(client, db_session)
        resp = client.post(f"/viewings?token={t_buy}",
                           json={"listing_id": lid, "viewing_at": "2026-06-15T10:00:00"})
        assert resp.status_code == 201

    def test_viewing_unauthenticated(self, client):
        resp = client.post("/viewings",
                           json={"listing_id": 1, "viewing_at": "2026-06-15T10:00:00"})
        assert resp.status_code in [401, 422]

    def test_get_my_viewings(self, client, db_session):
        t_own, t_buy, lid = setup_owner_and_buyer(client, db_session)
        client.post(f"/viewings?token={t_buy}",
                    json={"listing_id": lid, "viewing_at": "2026-06-15T10:00:00"})
        resp = client.get(f"/viewings/me?token={t_buy}")
        assert resp.status_code == 200
        assert len(resp.json().get("viewings", [])) >= 1

    def test_get_listing_viewings_owner(self, client, db_session):
        t_own, t_buy, lid = setup_owner_and_buyer(client, db_session)
        client.post(f"/viewings?token={t_buy}",
                    json={"listing_id": lid, "viewing_at": "2026-06-15T10:00:00"})
        resp = client.get(f"/listings/{lid}/viewings?token={t_own}")
        assert resp.status_code == 200


class TestViewingRespond:
    def test_owner_accepts_viewing(self, client, db_session):
        t_own, t_buy, lid = setup_owner_and_buyer(client, db_session)
        vid = client.post(f"/viewings?token={t_buy}",
                          json={"listing_id": lid, "viewing_at": "2026-06-15T10:00:00"}).json()["id"]
        resp = client.patch(f"/viewings/{vid}/respond?token={t_own}",
                            json={"action": "accept"})
        assert resp.status_code == 200

    def test_owner_rejects_viewing(self, client, db_session):
        t_own, t_buy, lid = setup_owner_and_buyer(client, db_session)
        vid = client.post(f"/viewings?token={t_buy}",
                          json={"listing_id": lid, "viewing_at": "2026-06-15T10:00:00"}).json()["id"]
        resp = client.patch(f"/viewings/{vid}/respond?token={t_own}",
                            json={"action": "reject"})
        assert resp.status_code == 200

    def test_requester_cancels_viewing(self, client, db_session):
        t_own, t_buy, lid = setup_owner_and_buyer(client, db_session)
        vid = client.post(f"/viewings?token={t_buy}",
                          json={"listing_id": lid, "viewing_at": "2026-06-15T10:00:00"}).json()["id"]
        resp = client.patch(f"/viewings/{vid}/cancel?token={t_buy}")
        assert resp.status_code == 200
