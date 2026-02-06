"""Tests for deal rating calculation and market price caching."""
import pytest
from datetime import datetime, timedelta

from app.models.route_market_price import RouteMarketPrice
from app.services.deal_rating import (
    calculate_rating,
    get_cached_market_price,
    save_market_price,
    RATING_LABELS,
    RATING_THRESHOLDS,
)


class TestCalculateRating:
    def test_hot_deal(self):
        # 40% savings = hot
        savings, label = calculate_rating(600, 1000)
        assert savings == 40.0
        assert label == RATING_LABELS["hot"]

    def test_good_deal(self):
        # 20% savings = good
        savings, label = calculate_rating(800, 1000)
        assert savings == 20.0
        assert label == RATING_LABELS["good"]

    def test_decent_deal(self):
        # 10% savings = decent
        savings, label = calculate_rating(900, 1000)
        assert savings == 10.0
        assert label == RATING_LABELS["decent"]

    def test_normal_price(self):
        # 3% savings = normal
        savings, label = calculate_rating(970, 1000)
        assert savings == pytest.approx(3.0)
        assert label == RATING_LABELS["normal"]

    def test_above_market(self):
        # -10% savings = above market
        savings, label = calculate_rating(1100, 1000)
        assert savings == -10.0
        assert label == RATING_LABELS["above"]

    def test_zero_market_price(self):
        savings, label = calculate_rating(500, 0)
        assert savings == 0.0
        assert label == RATING_LABELS["normal"]

    def test_negative_market_price(self):
        savings, label = calculate_rating(500, -100)
        assert savings == 0.0
        assert label == RATING_LABELS["normal"]

    def test_boundary_hot(self):
        # Exactly 30% savings
        savings, label = calculate_rating(700, 1000)
        assert savings == 30.0
        assert label == RATING_LABELS["hot"]

    def test_boundary_good(self):
        # Exactly 15% savings
        savings, label = calculate_rating(850, 1000)
        assert savings == 15.0
        assert label == RATING_LABELS["good"]

    def test_boundary_decent(self):
        # Exactly 5% savings
        savings, label = calculate_rating(950, 1000)
        assert savings == 5.0
        assert label == RATING_LABELS["decent"]


class TestMarketPriceCache:
    def test_save_and_retrieve(self, db_session):
        save_market_price(db_session, "AKL", "SYD", 500.0, "NZD", "serpapi")
        cached = get_cached_market_price(db_session, "AKL", "SYD")
        assert cached is not None
        assert cached.market_price == 500.0
        assert cached.origin == "AKL"
        assert cached.destination == "SYD"

    def test_case_insensitive_save(self, db_session):
        save_market_price(db_session, "akl", "syd", 500.0, "NZD", "serpapi")
        cached = get_cached_market_price(db_session, "AKL", "SYD")
        assert cached is not None

    def test_expired_cache_not_returned(self, db_session):
        mp = save_market_price(db_session, "AKL", "SYD", 500.0, "NZD", "serpapi")
        # Age it beyond 7 days
        mp.checked_at = datetime.utcnow() - timedelta(days=8)
        db_session.commit()
        cached = get_cached_market_price(db_session, "AKL", "SYD")
        assert cached is None

    def test_update_existing_averages(self, db_session):
        save_market_price(db_session, "AKL", "SYD", 500.0, "NZD", "serpapi")
        save_market_price(db_session, "AKL", "SYD", 600.0, "NZD", "serpapi")
        cached = get_cached_market_price(db_session, "AKL", "SYD")
        assert cached.market_price == pytest.approx(550.0)
        assert cached.sample_count == 2
        assert cached.min_price == 500.0
        assert cached.max_price == 600.0

    def test_different_routes_separate(self, db_session):
        save_market_price(db_session, "AKL", "SYD", 500.0, "NZD", "serpapi")
        save_market_price(db_session, "AKL", "LAX", 1500.0, "NZD", "serpapi")
        syd = get_cached_market_price(db_session, "AKL", "SYD")
        lax = get_cached_market_price(db_session, "AKL", "LAX")
        assert syd.market_price == 500.0
        assert lax.market_price == 1500.0

    def test_cabin_class_filtering(self, db_session):
        save_market_price(db_session, "AKL", "SYD", 500.0, "NZD", "serpapi", cabin_class="economy")
        save_market_price(db_session, "AKL", "SYD", 2000.0, "NZD", "serpapi", cabin_class="business")
        economy = get_cached_market_price(db_session, "AKL", "SYD", cabin_class="economy")
        business = get_cached_market_price(db_session, "AKL", "SYD", cabin_class="business")
        assert economy.market_price == 500.0
        assert business.market_price == 2000.0
