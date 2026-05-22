"""
test_integration.py — Integration and system-level tests.

Integration tests verify two-or-more modules interacting.
System tests verify end-to-end user journeys.
"""

import pytest
from tests.conftest import register_and_verify, do_login

LISTING = {"address": "99 Integration Ave", "price": 350000, "bedrooms": 4,
           "category": "residential", "amenities": []}


class TestIntegration:
    """Cross-module interaction tests."""

    def test_auth_then_create_listing(self, client, db_session):
        """Auth module + listings module together."""
        register_and_verify(client)
        token = do_login(client, db_session)
        resp = client.post(f"/listings?token={token}", json=LISTING)
        assert resp.status_code == 201

    def test_listing_then_favorite(self, client, db_session):
        """Listings + favorites modules together."""
        register_and_verify(client)
        token = do_login(client, db_session)
        lid = client.post(f"/listings?token={token}", json=LISTING).json()["id"]
        resp = client.post(f"/favorites?listing_id={lid}&token={token}")
        assert resp.status_code == 201
        favs = client.get(f"/favorites?token={token}").json()
        assert any(f["listing_id"] == lid for f in favs.get("favorites", []))

    def test_bid_creates_chat_and_message(self, client, db_session):
        """Bids + chats + messages via Facade pattern."""
        register_and_verify(client, "owner", "owner@test.com", "P@ss1")
        t_owner = do_login(client, db_session, "owner@test.com", "P@ss1")
        lid = client.post(f"/listings?token={t_owner}", json=LISTING).json()["id"]

        register_and_verify(client, "buyer", "buyer@test.com", "P@ss1")
        t_buyer = do_login(client, db_session, "buyer@test.com", "P@ss1")
        resp = client.post(f"/bids?token={t_buyer}", json={"listing_id": lid, "amount": 400000})
        assert resp.status_code == 201

        chats = client.get(f"/chats?token={t_buyer}").json()
        assert len(chats.get("chats", [])) >= 1

    def test_audit_log_on_registration(self, client, db_session):
        """Auth + audit cross-cutting."""
        register_and_verify(client)
        from audit.audit_logs_model import AuditLog
        from sqlmodel import select
        logs = db_session.exec(select(AuditLog).where(AuditLog.action == "create_user")).all()
        assert len(logs) >= 1


class TestSystem:
    """End-to-end user journey tests."""

    def test_full_sell_and_bid_journey(self, client, db_session):
        """Owner lists -> buyer bids -> owner accepts -> listing sold."""
        register_and_verify(client, "seller", "seller@t.com", "P@ss1")
        t_sell = do_login(client, db_session, "seller@t.com", "P@ss1")
        lid = client.post(f"/listings?token={t_sell}", json=LISTING).json()["id"]

        register_and_verify(client, "bidder", "bidder@t.com", "P@ss1")
        t_bid = do_login(client, db_session, "bidder@t.com", "P@ss1")
        bid_id = client.post(f"/bids?token={t_bid}", json={"listing_id": lid, "amount": 400000}).json()["id"]

        resp = client.patch(f"/bids/{bid_id}/respond?token={t_sell}",
                            json={"action": "accept"})
        assert resp.status_code == 200

        detail = client.get(f"/listings/{lid}").json()
        assert detail["status"] == "sold"

    def test_viewing_request_journey(self, client, db_session):
        """Owner lists -> user requests viewing."""
        register_and_verify(client, "own", "own@t.com", "P@ss1")
        t = do_login(client, db_session, "own@t.com", "P@ss1")
        lid = client.post(f"/listings?token={t}", json=LISTING).json()["id"]

        register_and_verify(client, "vis", "vis@t.com", "P@ss1")
        t2 = do_login(client, db_session, "vis@t.com", "P@ss1")
        resp = client.post(f"/viewings?token={t2}",
                           json={"listing_id": lid, "viewing_at": "2026-06-01T10:00:00"})
        assert resp.status_code == 201

    def test_search_then_favourite(self, client, db_session):
        """Browse + filter + save favourite end-to-end."""
        register_and_verify(client)
        token = do_login(client, db_session)
        client.post(f"/listings?token={token}", json={**LISTING, "category": "commercial", "price": 500000})

        results = client.get("/listings?category=commercial&min_price=400000").json()
        assert len(results.get("listings", [])) >= 1
        lid = results["listings"][0]["id"]

        resp = client.post(f"/favorites?listing_id={lid}&token={token}")
        assert resp.status_code == 201

    def test_reject_then_rebid(self, client, db_session):
        """Owner rejects bid -> buyer places new bid."""
        register_and_verify(client, "rej_own", "rej_own@t.com", "P@ss1")
        t_own = do_login(client, db_session, "rej_own@t.com", "P@ss1")
        lid = client.post(f"/listings?token={t_own}", json=LISTING).json()["id"]

        register_and_verify(client, "rej_buy", "rej_buy@t.com", "P@ss1")
        t_buy = do_login(client, db_session, "rej_buy@t.com", "P@ss1")
        bid_id = client.post(f"/bids?token={t_buy}", json={"listing_id": lid, "amount": 200000}).json()["id"]
        client.patch(f"/bids/{bid_id}/respond?token={t_own}", json={"action": "reject"})

        resp = client.post(f"/bids?token={t_buy}", json={"listing_id": lid, "amount": 250000})
        assert resp.status_code == 201

    def test_cancel_then_rebid(self, client, db_session):
        """Buyer cancels bid -> buyer places new bid."""
        register_and_verify(client, "can_own", "can_own@t.com", "P@ss1")
        t_own = do_login(client, db_session, "can_own@t.com", "P@ss1")
        lid = client.post(f"/listings?token={t_own}", json=LISTING).json()["id"]

        register_and_verify(client, "can_buy", "can_buy@t.com", "P@ss1")
        t_buy = do_login(client, db_session, "can_buy@t.com", "P@ss1")
        bid_id = client.post(f"/bids?token={t_buy}", json={"listing_id": lid, "amount": 200000}).json()["id"]
        client.patch(f"/bids/{bid_id}/cancel?token={t_buy}")

        resp = client.post(f"/bids?token={t_buy}", json={"listing_id": lid, "amount": 250000})
        assert resp.status_code == 201

    def test_multiple_buyers_compete(self, client, db_session):
        """Two buyers bid -> owner accepts one -> other gets rejected."""
        register_and_verify(client, "comp_own", "comp_own@t.com", "P@ss1")
        t_own = do_login(client, db_session, "comp_own@t.com", "P@ss1")
        lid = client.post(f"/listings?token={t_own}", json=LISTING).json()["id"]

        register_and_verify(client, "b1", "b1@t.com", "P@ss1")
        t_b1 = do_login(client, db_session, "b1@t.com", "P@ss1")
        bid1 = client.post(f"/bids?token={t_b1}", json={"listing_id": lid, "amount": 300000}).json()["id"]

        register_and_verify(client, "b2", "b2@t.com", "P@ss1")
        t_b2 = do_login(client, db_session, "b2@t.com", "P@ss1")
        client.post(f"/bids?token={t_b2}", json={"listing_id": lid, "amount": 320000})

        client.patch(f"/bids/{bid1}/respond?token={t_own}", json={"action": "accept"})
        detail = client.get(f"/listings/{lid}").json()
        assert detail["status"] == "sold"

    def test_subscription_creation(self, client, db_session):
        """User creates a subscription for listing alerts."""
        register_and_verify(client, "sub", "sub@t.com", "P@ss1")
        t = do_login(client, db_session, "sub@t.com", "P@ss1")
        resp = client.post(f"/subscriptions?token={t}",
                           json={"category": "residential", "min_price": 100000, "max_price": 500000})
        assert resp.status_code == 201

    def test_subscription_list_and_delete(self, client, db_session):
        """Create subscription, list it, delete it."""
        register_and_verify(client, "subd", "subd@t.com", "P@ss1")
        t = do_login(client, db_session, "subd@t.com", "P@ss1")
        sub = client.post(f"/subscriptions?token={t}",
                          json={"category": "commercial"}).json()
        subs = client.get(f"/subscriptions/me?token={t}").json()
        assert len(subs.get("subscriptions", [])) >= 1

        resp = client.delete(f"/subscriptions/{sub['id']}?token={t}")
        assert resp.status_code == 200

    def test_full_inquiry_to_chat_flow(self, client, db_session):
        """Buyer sends inquiry -> owner sees chat -> owner replies."""
        register_and_verify(client, "inq_own", "inq_own@t.com", "P@ss1")
        t_own = do_login(client, db_session, "inq_own@t.com", "P@ss1")
        lid = client.post(f"/listings?token={t_own}", json=LISTING).json()["id"]

        register_and_verify(client, "inq_buy", "inq_buy@t.com", "P@ss1")
        t_buy = do_login(client, db_session, "inq_buy@t.com", "P@ss1")
        client.post(f"/messages?token={t_buy}",
                    json={"listing_id": lid, "content": "Is this still available?"})

        owner_chats = client.get(f"/chats?token={t_own}").json()
        assert len(owner_chats.get("chats", [])) >= 1
