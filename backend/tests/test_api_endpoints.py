"""Tests for API endpoints."""
import pytest
from datetime import datetime

from app.models.deal import Deal, DealSource
from app.models.user_settings import UserSettings
from app.models.trip_plan import TripPlan
from app.models.search_definition import SearchDefinition


class TestHealthEndpoint:
    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestSettingsAPI:
    async def test_get_settings(self, client, db_session):
        UserSettings.get_or_create(db_session)
        response = await client.get("/settings/api/settings")
        assert response.status_code == 200
        data = response.json()
        assert data["home_airport"] == "AKL"
        assert "home_airports" in data

    async def test_update_settings(self, client, db_session):
        UserSettings.get_or_create(db_session)
        response = await client.put(
            "/settings/api/settings",
            json={"home_airport": "WLG", "preferred_currency": "USD"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["home_airport"] == "WLG"
        assert data["preferred_currency"] == "USD"


class TestDealsAPI:
    async def test_list_deals_empty(self, client, db_session):
        UserSettings.get_or_create(db_session)
        response = await client.get("/deals/api/deals")
        assert response.status_code == 200
        data = response.json()
        assert "deals" in data
        assert data["count"] == 0

    async def test_list_deals_with_data(self, client, db_session):
        UserSettings.get_or_create(db_session)
        deal = Deal(
            source=DealSource.SECRET_FLYING,
            link="https://example.com/deal1",
            raw_title="AKL to SYD $300",
            parsed_origin="AKL",
            parsed_destination="SYD",
            parsed_price=300,
            parsed_currency="NZD",
            is_relevant=True,
        )
        db_session.add(deal)
        db_session.commit()

        response = await client.get("/deals/api/deals", params={"relevant": True})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1


class TestTripsAPI:
    async def test_list_trips_empty(self, client, db_session):
        response = await client.get("/trips/api/trips")
        assert response.status_code == 200

    async def test_create_trip(self, client, db_session):
        UserSettings.get_or_create(db_session)
        response = await client.post(
            "/trips/api/trips",
            json={
                "name": "Test Trip",
                "origins": ["AKL"],
                "destinations": ["SYD"],
                "trip_duration_min": 3,
                "trip_duration_max": 7,
                "budget_max": 2000,
                "budget_currency": "NZD",
                "cabin_classes": ["economy"],
                "travelers_adults": 2,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Trip"
        assert data["origins"] == ["AKL"]
        assert data["id"] is not None

    async def test_create_trip_with_legs(self, client, db_session):
        UserSettings.get_or_create(db_session)
        response = await client.post(
            "/trips/api/trips",
            json={
                "name": "Multi-City Trip",
                "origins": [],
                "destinations": [],
                "legs": [
                    {"origin": "AKL", "destination": "NRT", "order": 0},
                    {"origin": "NRT", "destination": "ICN", "order": 1},
                    {"origin": "ICN", "destination": "AKL", "order": 2},
                ],
                "trip_duration_min": 10,
                "trip_duration_max": 21,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Multi-City Trip"
        assert len(data["legs"]) == 3
        assert data["legs"][0]["origin"] == "AKL"
        assert data["legs"][0]["destination"] == "NRT"

    async def test_get_trip(self, client, db_session):
        UserSettings.get_or_create(db_session)
        trip = TripPlan(
            name="Get Trip Test",
            origins=["AKL"],
            destinations=["NAN"],
            cabin_classes=["economy"],
        )
        db_session.add(trip)
        db_session.commit()
        response = await client.get(f"/trips/api/trips/{trip.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Get Trip Test"

    async def test_toggle_trip(self, client, db_session):
        UserSettings.get_or_create(db_session)
        trip = TripPlan(
            name="Toggle Test",
            origins=["AKL"],
            destinations=["SYD"],
            is_active=True,
        )
        db_session.add(trip)
        db_session.commit()
        response = await client.put(f"/trips/api/trips/{trip.id}/toggle")
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    async def test_delete_trip(self, client, db_session):
        UserSettings.get_or_create(db_session)
        trip = TripPlan(
            name="Delete Test",
            origins=["AKL"],
            destinations=["SYD"],
        )
        db_session.add(trip)
        db_session.commit()
        trip_id = trip.id
        response = await client.delete(f"/trips/api/trips/{trip_id}")
        assert response.status_code == 200
        assert response.json()["deleted"] is True

    async def test_create_trip_invalid_origin(self, client, db_session):
        UserSettings.get_or_create(db_session)
        response = await client.post(
            "/trips/api/trips",
            json={
                "name": "Bad Trip",
                "origins": ["ZZZZ"],
                "destinations": ["SYD"],
            },
        )
        assert response.status_code == 400


class TestSearchDefinitionsAPI:
    async def test_list_searches(self, client, db_session):
        response = await client.get("/prices/searches")
        assert response.status_code == 200

    async def test_create_search(self, client, db_session):
        response = await client.post(
            "/prices/searches",
            json={
                "origin": "AKL",
                "destination": "SYD",
                "trip_type": "round_trip",
                "adults": 2,
                "cabin_class": "economy",
                "stops_filter": "any",
                "currency": "NZD",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["origin"] == "AKL"
        assert data["destination"] == "SYD"
