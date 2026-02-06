"""Tests for price analysis functions."""
import pytest

from app.services.price_analyzer import (
    robust_z_score,
    calculate_percentile,
    is_absolute_new_low,
)


class TestRobustZScore:
    def test_below_median_is_negative(self):
        history = [100, 200, 300, 400, 500]
        z = robust_z_score(100, history)
        assert z < 0

    def test_above_median_is_positive(self):
        history = [100, 200, 300, 400, 500]
        z = robust_z_score(500, history)
        assert z > 0

    def test_at_median_is_zero(self):
        history = [100, 200, 300, 400, 500]
        z = robust_z_score(300, history)
        assert z == 0.0

    def test_single_value_returns_zero(self):
        assert robust_z_score(100, [100]) == 0.0

    def test_empty_history_returns_zero(self):
        assert robust_z_score(100, []) == 0.0

    def test_all_same_values(self):
        # When all values are the same, mad = 0, so fallback used
        history = [500, 500, 500, 500]
        z = robust_z_score(400, history)
        assert z < 0  # Below all-same median

    def test_outlier_robustness(self):
        # MAD should be robust to outliers unlike stddev
        normal = [100, 110, 105, 108, 102, 107, 103]
        z_normal = robust_z_score(80, normal)
        # Add an outlier
        with_outlier = normal + [1000]
        z_outlier = robust_z_score(80, with_outlier)
        # With MAD, the z-score should be similar despite the outlier
        # (stddev would be drastically different)
        assert abs(z_normal - z_outlier) < abs(z_normal) * 0.5

    def test_scaling_factor(self):
        # 1.4826 scaling makes MAD comparable to stddev for normal distributions
        import statistics
        # For a roughly normal distribution
        history = [90, 95, 100, 105, 110, 95, 105, 100, 100, 100]
        z = robust_z_score(80, history)
        # Should be a meaningful negative z-score
        assert z < -1


class TestCalculatePercentile:
    def test_lowest_price(self):
        history = [100, 200, 300, 400, 500]
        pct = calculate_percentile(50, history)
        assert pct == 100.0  # All prices are >= 50

    def test_highest_price(self):
        history = [100, 200, 300, 400, 500]
        pct = calculate_percentile(600, history)
        assert pct == 0.0  # No prices are >= 600

    def test_median_price(self):
        history = [100, 200, 300, 400, 500]
        pct = calculate_percentile(300, history)
        # 3 out of 5 prices >= 300
        assert pct == 60.0

    def test_empty_history(self):
        assert calculate_percentile(100, []) == 50.0

    def test_all_same(self):
        history = [100, 100, 100]
        pct = calculate_percentile(100, history)
        assert pct == 100.0  # All >= 100


class TestIsAbsoluteNewLow:
    def test_new_low(self):
        history = [200, 300, 250, 280]
        assert is_absolute_new_low(150, history) is True

    def test_not_new_low(self):
        history = [200, 300, 250, 280]
        assert is_absolute_new_low(220, history) is False

    def test_within_margin(self):
        history = [200, 300, 250, 280]
        # 2% margin means threshold = 200 * 1.02 = 204
        assert is_absolute_new_low(203, history, margin_percent=2.0) is True

    def test_exact_match(self):
        history = [200, 300, 250]
        assert is_absolute_new_low(200, history) is True

    def test_empty_history(self):
        assert is_absolute_new_low(100, []) is False

    def test_custom_margin(self):
        history = [100, 200, 300]
        # 10% margin: threshold = 100 * 1.10 = 110
        assert is_absolute_new_low(109, history, margin_percent=10.0) is True
        assert is_absolute_new_low(111, history, margin_percent=10.0) is False
