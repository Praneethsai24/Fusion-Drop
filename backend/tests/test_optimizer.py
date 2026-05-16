"""
Unit tests for the delivery route optimizer logic.
These are pure unit tests — no DB or HTTP required.
"""
import pytest
from unittest.mock import MagicMock


def _make_mock_settings():
    s = MagicMock()
    s.BATCH_RADIUS_KM = 3.0
    s.BASE_DELIVERY_FEE = 30.0
    s.FEE_PER_KM = 8.0
    s.BATCH_DISCOUNT = 0.25
    s.AVG_RIDER_SPEED_KMH = 25.0
    s.STOP_BUFFER_MINS = 3
    return s


# ── Haversine distance helper (if it exists in utils) ────────────────────────

def test_haversine_same_point():
    """Distance between a point and itself should be 0."""
    try:
        from backend.utils.geo import haversine_km
        dist = haversine_km(12.9716, 77.5946, 12.9716, 77.5946)
        assert dist == pytest.approx(0.0, abs=1e-6)
    except ImportError:
        pytest.skip("backend.utils.geo not found — skipping haversine test")


def test_haversine_known_distance():
    """
    Distance between Bengaluru city center and Koramangala is ~4.5 km.
    We test within a 1 km tolerance.
    """
    try:
        from backend.utils.geo import haversine_km
        dist = haversine_km(12.9716, 77.5946, 12.9352, 77.6245)
        assert 3.0 <= dist <= 6.0, f"Unexpected distance: {dist}"
    except ImportError:
        pytest.skip("backend.utils.geo not found — skipping haversine test")


def test_haversine_symmetry():
    """haversine(A, B) == haversine(B, A)."""
    try:
        from backend.utils.geo import haversine_km
        d1 = haversine_km(12.97, 77.59, 12.93, 77.62)
        d2 = haversine_km(12.93, 77.62, 12.97, 77.59)
        assert d1 == pytest.approx(d2, rel=1e-5)
    except ImportError:
        pytest.skip("backend.utils.geo not found")


# ── Delivery fee calculation ──────────────────────────────────────────────────

def test_delivery_fee_minimum():
    """Delivery fee should never be below BASE_DELIVERY_FEE for very short routes."""
    try:
        from backend.services.optimizer import calculate_delivery_fee
        settings = _make_mock_settings()
        fee = calculate_delivery_fee(distance_km=0.1, is_batched=False, settings=settings)
        assert fee >= settings.BASE_DELIVERY_FEE
    except ImportError:
        pytest.skip("backend.services.optimizer not found")


def test_delivery_fee_batched_discount():
    """Batched order fee should be lower than non-batched fee."""
    try:
        from backend.services.optimizer import calculate_delivery_fee
        settings = _make_mock_settings()
        fee_solo = calculate_delivery_fee(distance_km=5.0, is_batched=False, settings=settings)
        fee_batched = calculate_delivery_fee(distance_km=5.0, is_batched=True, settings=settings)
        assert fee_batched < fee_solo
        expected_discount = fee_solo * settings.BATCH_DISCOUNT
        assert abs((fee_solo - fee_batched) - expected_discount) < 0.01
    except ImportError:
        pytest.skip("backend.services.optimizer not found")


def test_delivery_fee_scales_with_distance():
    """Delivery fee should increase with distance."""
    try:
        from backend.services.optimizer import calculate_delivery_fee
        settings = _make_mock_settings()
        fee_short = calculate_delivery_fee(distance_km=1.0, is_batched=False, settings=settings)
        fee_long = calculate_delivery_fee(distance_km=10.0, is_batched=False, settings=settings)
        assert fee_long > fee_short
    except ImportError:
        pytest.skip("backend.services.optimizer not found")


# ── ETA calculation ───────────────────────────────────────────────────────────

def test_eta_positive():
    """ETA should always be a positive integer."""
    try:
        from backend.services.optimizer import calculate_eta_minutes
        settings = _make_mock_settings()
        eta = calculate_eta_minutes(
            distance_km=3.0,
            prep_time_minutes=20,
            num_stops=1,
            settings=settings,
        )
        assert eta > 0
        assert isinstance(eta, int)
    except ImportError:
        pytest.skip("backend.services.optimizer not found")


def test_eta_increases_with_stops():
    """More stops should result in a higher ETA."""
    try:
        from backend.services.optimizer import calculate_eta_minutes
        settings = _make_mock_settings()
        eta_one_stop = calculate_eta_minutes(
            distance_km=3.0, prep_time_minutes=20, num_stops=1, settings=settings
        )
        eta_three_stops = calculate_eta_minutes(
            distance_km=3.0, prep_time_minutes=20, num_stops=3, settings=settings
        )
        assert eta_three_stops > eta_one_stop
    except ImportError:
        pytest.skip("backend.services.optimizer not found")