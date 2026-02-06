"""Tests for DealScorer service."""
import pytest
from datetime import datetime, timedelta

from app.models.deal import Deal, DealSource
from app.models.user_settings import UserSettings
from app.services.deal_scorer import DealScorer, PREMIUM_AIRLINES, BUDGET_AIRLINES


def _make_deal(
    origin="AKL",
    destination="SYD",
    price=500,
    currency="NZD",
    airline=None,
    cabin_class=None,
    is_relevant=True,
    relevance_reason="From AKL",
    published_at=None,
    source=DealSource.SECRET_FLYING,
):
    return Deal(
        source=source,
        link=f"https://example.com/{origin}-{destination}",
        raw_title=f"Deal: {origin} to {destination}",
        parsed_origin=origin,
        parsed_destination=destination,
        parsed_price=price,
        parsed_currency=currency,
        parsed_airline=airline,
        parsed_cabin_class=cabin_class,
        is_relevant=is_relevant,
        relevance_reason=relevance_reason,
        published_at=published_at or datetime.utcnow(),
    )


class TestScoreRelevance:
    def test_home_airport_origin_scores_40(self, db_session):
        UserSettings.get_or_create(db_session)  # Creates with home_airport=AKL
        scorer = DealScorer(db_session)
        deal = _make_deal(origin="AKL", relevance_reason="From AKL")
        assert scorer._score_relevance(deal) == 40.0

    def test_watched_destination_scores_35(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(origin="LAX", destination="SYD", relevance_reason="other")
        # SYD is in default watched_destinations
        assert scorer._score_relevance(deal) == 35.0

    def test_similar_destination_scores_25(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(origin="LAX", destination="BKK", relevance_reason="Similar to Singapore")
        assert scorer._score_relevance(deal) == 25.0

    def test_oceania_deal_scores_15(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(origin="MEL", destination="BKK", relevance_reason="Oceania hub")
        assert scorer._score_relevance(deal) == 15.0

    def test_irrelevant_deal_scores_0(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(is_relevant=False)
        assert scorer._score_relevance(deal) == 0.0

    def test_default_relevant_scores_10(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(origin="JFK", destination="CDG", relevance_reason="something else")
        assert scorer._score_relevance(deal) == 10.0


class TestScoreValue:
    def test_economy_very_cheap(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(price=150, cabin_class="ECONOMY")
        assert scorer._score_value(deal) == 30.0

    def test_economy_cheap(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(price=350, cabin_class="ECONOMY")
        assert scorer._score_value(deal) == 25.0

    def test_economy_mid(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(price=550, cabin_class="ECONOMY")
        assert scorer._score_value(deal) == 20.0

    def test_economy_expensive(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(price=800, cabin_class="ECONOMY")
        assert scorer._score_value(deal) == 15.0

    def test_economy_very_expensive(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(price=1500, cabin_class="ECONOMY")
        assert scorer._score_value(deal) == 10.0

    def test_business_cheap(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(price=1200, cabin_class="BUSINESS")
        assert scorer._score_value(deal) == 30.0

    def test_first_cheap(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(price=2500, cabin_class="FIRST")
        assert scorer._score_value(deal) == 30.0

    def test_no_price_scores_10(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(price=None)
        assert scorer._score_value(deal) == 10.0


class TestScoreRecency:
    def test_very_fresh(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(published_at=datetime.utcnow() - timedelta(hours=2))
        assert scorer._score_recency(deal) == 20.0

    def test_same_day(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(published_at=datetime.utcnow() - timedelta(hours=12))
        assert scorer._score_recency(deal) == 18.0

    def test_one_day_old(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(published_at=datetime.utcnow() - timedelta(days=1, hours=6))
        assert scorer._score_recency(deal) == 15.0

    def test_week_old(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(published_at=datetime.utcnow() - timedelta(days=5))
        assert scorer._score_recency(deal) == 8.0

    def test_very_old(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(published_at=datetime.utcnow() - timedelta(days=14))
        assert scorer._score_recency(deal) == 5.0

    def test_no_published_date(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(published_at=None)
        deal.published_at = None
        assert scorer._score_recency(deal) == 10.0


class TestScoreQuality:
    def test_premium_airline_bonus(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(airline="Singapore Airlines")
        assert scorer._score_quality(deal) == 8.0  # 5 base + 3 premium

    def test_budget_airline_penalty(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(airline="Jetstar")
        assert scorer._score_quality(deal) == 3.0  # 5 base - 2 budget

    def test_business_class_bonus(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(airline="Unknown Airline", cabin_class="BUSINESS")
        assert scorer._score_quality(deal) == 7.0  # 5 base + 2 cabin

    def test_premium_business_combo(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(airline="Qatar Airways", cabin_class="FIRST")
        assert scorer._score_quality(deal) == 10.0  # 5 + 3 + 2

    def test_unknown_airline_base(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(airline="Unknown Carrier")
        assert scorer._score_quality(deal) == 5.0


class TestOverallScore:
    def test_score_bounded_0_to_100(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal()
        score = scorer.score_deal(deal)
        assert 0.0 <= score <= 100.0

    def test_perfect_deal(self, db_session):
        """Home airport, cheap economy, very fresh, premium airline."""
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(
            origin="AKL",
            price=150,
            cabin_class="ECONOMY",
            airline="Air New Zealand",
            published_at=datetime.utcnow() - timedelta(hours=1),
            relevance_reason="From AKL",
        )
        score = scorer.score_deal(deal)
        # relevance=40 + value=30 + recency=20 + quality=8 = 98
        assert score >= 90.0

    def test_irrelevant_deal_low_score(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal(is_relevant=False, price=2000)
        score = scorer.score_deal(deal)
        # relevance=0, so score should be well below 50
        assert score < 50.0

    def test_update_deal_score_persists(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        deal = _make_deal()
        db_session.add(deal)
        db_session.commit()
        scorer.update_deal_score(deal)
        assert deal.score > 0

    def test_get_top_deals(self, db_session):
        UserSettings.get_or_create(db_session)
        scorer = DealScorer(db_session)
        for i in range(5):
            d = _make_deal(price=100 + i * 200)
            d.score = 80 - i * 10
            d.is_relevant = True
            db_session.add(d)
        db_session.commit()
        top = scorer.get_top_deals(limit=3)
        assert len(top) == 3
        assert top[0].score >= top[1].score >= top[2].score
