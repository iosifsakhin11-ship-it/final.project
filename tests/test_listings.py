"""
test_listings.py — Unit tests for the listings module.

Covers: create, browse, filters (category, price, bedrooms),
detail view, update, delete, owner-only checks.
"""

import pytest
from tests.conftest import register_and_verify, do_login

LISTING = {"address": "123 Test St", "price": 250000, "bedrooms": 3,
           "category": "residential", "amenities": []}


class TestCreateListing:
    def test_create_success(self, client, db_session):
        register_and_verify(client)
        token = do_login(client, db_session)
        resp = client.post(f"/listings?token={token}", json=LISTING)
        assert resp.status_code == 201
        assert resp.json()["address"] == "123 Test St"

    def test_create_unauthenticated(self, client):
        resp = client.post("/listings", json=LISTING)
        assert resp.status_code in [401, 422]


class TestBrowseListings:
    def test_browse_empty(self, client):
        resp = client.get("/listings")
        assert resp.status_code == 200

    def test_browse_returns_active(self, client, db_session):
        register_and_verify(client)
        token = do_login(client, db_session)
        client.post(f"/listings?token={token}", json=LISTING)
        resp = client.get("/listings")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data.get("items", [])) >= 1

    def test_filter_by_category(self, client, db_session):
        register_and_verify(client)
        token = do_login(client, db_session)
        client.post(f"/listings?token={token}", json={**LISTING, "category": "commercial"})
        client.post(f"/listings?token={token}", json={**LISTING, "category": "residential"})
        resp = client.get("/listings?category=commercial")
        listings = resp.json().get("items", [])
        assert all(l["category"] == "commercial" for l in listings)

    def test_filter_by_price_range(self, client, db_session):
        register_and_verify(client)
        token = do_login(client, db_session)
        client.post(f"/listings?token={token}", json={**LISTING, "price": 100000})
        client.post(f"/listings?token={token}", json={**LISTING, "price": 500000})
        resp = client.get("/listings?min_price=200000&max_price=600000")
        listings = resp.json().get("items", [])
        for l in listings:
            assert float(l["price"]) >= 200000

    def test_filter_by_bedrooms(self, client, db_session):
        register_and_verify(client)
        token = do_login(client, db_session)
        client.post(f"/listings?token={token}", json={**LISTING, "bedrooms": 5})
        resp = client.get("/listings?bedrooms=5")
        listings = resp.json().get("items", [])
        assert all(l["bedrooms"] == 5 for l in listings)

    def test_filter_by_location(self, client, db_session):
        """FR-6: Location filter — substring match on address."""
        register_and_verify(client)
        token = do_login(client, db_session)
        client.post(f"/listings?token={token}", json={**LISTING, "address": "Athens Central"})
        client.post(f"/listings?token={token}", json={**LISTING, "address": "London Bridge"})
        resp = client.get("/listings?location=Athens")
        listings = resp.json().get("items", [])
        assert len(listings) >= 1
        assert all("Athens" in l["address"] for l in listings)

    def test_filter_by_location_case_insensitive(self, client, db_session):
        """FR-6: Location search must be case-insensitive."""
        register_and_verify(client)
        token = do_login(client, db_session)
        client.post(f"/listings?token={token}", json={**LISTING, "address": "PARIS Downtown"})
        resp = client.get("/listings?location=paris")
        listings = resp.json().get("items", [])
        assert len(listings) >= 1

    def test_filter_by_amenities(self, client, db_session):
        """FR-6: Amenities filter — matches JSON array content."""
        register_and_verify(client)
        token = do_login(client, db_session)
        client.post(f"/listings?token={token}", json={**LISTING, "amenities": ["pool", "garden", "parking"]})
        client.post(f"/listings?token={token}", json={**LISTING, "amenities": ["gym"]})
        resp = client.get("/listings?amenities=pool")
        listings = resp.json().get("items", [])
        assert len(listings) >= 1

    def test_combined_filters(self, client, db_session):
        """FR-6: Multiple filters applied together."""
        register_and_verify(client)
        token = do_login(client, db_session)
        client.post(f"/listings?token={token}", json={
            "address": "Athens Villa", "price": 300000, "bedrooms": 4,
            "category": "residential", "amenities": ["pool"]
        })
        resp = client.get("/listings?location=Athens&category=residential&min_price=200000&bedrooms=4")
        listings = resp.json().get("items", [])
        assert len(listings) >= 1


class TestListingDetail:
    def test_view_detail_public(self, client, db_session):
        register_and_verify(client)
        token = do_login(client, db_session)
        create = client.post(f"/listings?token={token}", json=LISTING)
        lid = create.json()["id"]
        resp = client.get(f"/listings/{lid}")
        assert resp.status_code == 200

    def test_view_nonexistent(self, client):
        resp = client.get("/listings/99999")
        assert resp.status_code == 404


class TestUpdateDelete:
    def test_update_own_listing(self, client, db_session):
        register_and_verify(client)
        token = do_login(client, db_session)
        create = client.post(f"/listings?token={token}", json=LISTING)
        lid = create.json()["id"]
        resp = client.patch(f"/listings/{lid}?token={token}", json={"price": 300000})
        assert resp.status_code == 200

    def test_delete_own_listing(self, client, db_session):
        register_and_verify(client)
        token = do_login(client, db_session)
        create = client.post(f"/listings?token={token}", json=LISTING)
        lid = create.json()["id"]
        resp = client.delete(f"/listings/{lid}?token={token}")
        assert resp.status_code == 200

    def test_delete_not_owner(self, client, db_session):
        register_and_verify(client, "owner", "owner@test.com", "P@ss1")
        t1 = do_login(client, db_session, "owner@test.com", "P@ss1")
        create = client.post(f"/listings?token={t1}", json=LISTING)
        lid = create.json()["id"]

        register_and_verify(client, "other", "other@test.com", "P@ss1")
        t2 = do_login(client, db_session, "other@test.com", "P@ss1")
        resp = client.delete(f"/listings/{lid}?token={t2}")
        assert resp.status_code == 403
