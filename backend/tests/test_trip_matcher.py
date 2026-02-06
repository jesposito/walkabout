"""Tests for TripMatcher service."""
import pytest
from datetime import datetime
from unittest.mock import patch

from app.models.deal import Deal, DealSource
from app.models.trip_plan import TripPlan
from app.models.user_settings import UserSettings
from app.services.trip_matcher import TripMatcher


def _make_deal(
    origin="AKL",
    destination="SYD",
    price=500,
    currency="NZD",
    airline=None,
    cabin_class="economy",
    link_suffix="",
):
    return Deal(
        source=DealSource.SECRET_FLYING,
        link=f"https://example.com/{origin}-{destination}{link_suffix}",
        raw_title=f"Deal: {origin} to {destination}",
        parsed_origin=origin,
        parsed_destination=destination,
        parsed_price=price,
        parsed_currency=currency,
        parsed_airline=airline,
        parsed_cabin_class=cabin_class,
        is_relevant=True,
        published_at=datetime.utcnow(),
    )


def _make_plan(
    name="Test Trip",
    origins=None,
    destinations=None,
    destination_types=None,
    budget_max=None,
    budget_currency="NZD",
    cabin_classes=None,
):
    return TripPlan(
        name=name,
        origins=origins or ["AKL"],
        destinations=destinations or ["SYD"],
        destination_types=destination_types or [],
        budget_max=budget_max,
        budget_currency=budget_currency,
        cabin_classes=cabin_classes or ["economy"],
        travelers_adults=2,
        travelers_children=0,
        is_active=True,
    )


class TestScoreMatchOrigin:
    def test_exact_origin_match(self, db_session):
        matcher = TripMatcher(db_session)
        deal = _make_deal(origin="AKL")
        plan = _make_plan(origins=["AKL"])
        score = matcher._score_match(deal, plan)
        assert score >= 30  # 30 for exact origin

    def test_no_origin_match_returns_zero(self, db_session):
        matcher = TripMatcher(db_session)
        deal = _make_deal(origin="JFK")
        plan = _make_plan(origins=["AKL"], destinations=["SYD"])
        # JFK not in plan origins and not similar to AKL
        with patch("app.services.trip_matcher.DestinationService") as mock_ds:
            mock_ds.get_similar_airports.return_value = set()
            score = matcher._score_match(deal, plan)
        assert score == 0.0

    def test_no_origins_specified_still_matches(self, db_session):
        matcher = TripMatcher(db_session)
        deal = _make_deal(origin="JFK")
        plan = _make_plan(origins=[], destinations=["SYD"])
        deal.parsed_destination = "SYD"
        score = matcher._score_match(deal, plan)
        # No origin filter = 10 points + dest match
        assert score >= 10


class TestScoreMatchDestination:
    def test_exact_destination_match(self, db_session):
        matcher = TripMatcher(db_session)
        deal = _make_deal(destination="SYD")
        plan = _make_plan(destinations=["SYD"])
        score = matcher._score_match(deal, plan)
        assert score >= 30  # 30 for exact dest

    def test_no_destinations_specified(self, db_session):
        matcher = TripMatcher(db_session)
        deal = _make_deal(origin="AKL", destination="NRT")
        plan = _make_plan(origins=["AKL"], destinations=[])
        plan.destination_types = []
        score = matcher._score_match(deal, plan)
        # Origin match + no dest filter
        assert score > 0


class TestScoreMatchBudget:
    def test_under_budget_bonus(self, db_session):
        matcher = TripMatcher(db_session)
        deal = _make_deal(price=400)
        plan = _make_plan(budget_max=1000)
        score_with_budget = matcher._score_match(deal, plan)

        deal2 = _make_deal(price=400, link_suffix="-2")
        plan2 = _make_plan(budget_max=None)
        score_no_budget = matcher._score_match(deal2, plan2)

        assert score_with_budget > score_no_budget

    def test_way_over_budget_returns_zero(self, db_session):
        matcher = TripMatcher(db_session)
        deal = _make_deal(price=1500)
        plan = _make_plan(budget_max=1000)
        # 50% over budget (>20%) should return 0
        score = matcher._score_match(deal, plan)
        assert score == 0.0

    def test_slightly_over_budget_penalized(self, db_session):
        matcher = TripMatcher(db_session)
        deal = _make_deal(price=1100)
        plan = _make_plan(budget_max=1000)
        # 10% over budget (<20%) should still match but with penalty
        score = matcher._score_match(deal, plan)
        assert score > 0


class TestScoreMatchCabin:
    def test_matching_cabin_bonus(self, db_session):
        matcher = TripMatcher(db_session)
        deal = _make_deal(cabin_class="economy")
        plan = _make_plan(cabin_classes=["economy"])
        score = matcher._score_match(deal, plan)
        # Should include 10 points for cabin match
        assert score >= 10

    def test_no_cabin_filter(self, db_session):
        matcher = TripMatcher(db_session)
        deal = _make_deal(cabin_class="business")
        plan = _make_plan(cabin_classes=[])
        score = matcher._score_match(deal, plan)
        # No cabin filter = no bonus, but doesn't disqualify
        assert score > 0


class TestMatchDealToPlans:
    def test_matches_active_plans_only(self, db_session):
        active_plan = _make_plan(name="Active")
        active_plan.is_active = True
        inactive_plan = _make_plan(name="Inactive")
        inactive_plan.is_active = False
        db_session.add_all([active_plan, inactive_plan])
        db_session.commit()

        matcher = TripMatcher(db_session)
        deal = _make_deal(origin="AKL", destination="SYD")
        matches = matcher.match_deal_to_plans(deal)
        plan_names = [p.name for p, _ in matches]
        assert "Active" in plan_names
        assert "Inactive" not in plan_names

    def test_sorted_by_score_descending(self, db_session):
        plan1 = _make_plan(name="Exact", origins=["AKL"], destinations=["SYD"])
        plan2 = _make_plan(name="Open", origins=[], destinations=[])
        plan2.destination_types = []
        db_session.add_all([plan1, plan2])
        db_session.commit()

        matcher = TripMatcher(db_session)
        deal = _make_deal(origin="AKL", destination="SYD")
        matches = matcher.match_deal_to_plans(deal)
        if len(matches) >= 2:
            assert matches[0][1] >= matches[1][1]


class TestUpdatePlanMatches:
    def test_updates_match_count(self, db_session):
        plan = _make_plan()
        db_session.add(plan)
        deal = _make_deal()
        deal.is_relevant = True
        db_session.add(deal)
        db_session.commit()

        matcher = TripMatcher(db_session)
        count = matcher.update_plan_matches(plan)
        assert count >= 1
        assert plan.match_count >= 1

    def test_zero_matches(self, db_session):
        plan = _make_plan(origins=["ZZZ"], destinations=["ZZZ"])
        db_session.add(plan)
        db_session.commit()

        matcher = TripMatcher(db_session)
        with patch("app.services.trip_matcher.DestinationService") as mock_ds:
            mock_ds.get_similar_airports.return_value = set()
            count = matcher.update_plan_matches(plan)
        assert count == 0
