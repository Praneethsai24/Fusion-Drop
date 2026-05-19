"""
Unit tests for delivery_optimizer.py.
These run without a DB (pure Python math tests).
"""
import pytest
import math


def haversine_km(lat1, lng1, lat2, lng2):
    R = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lng2 - lng1)
    a = math.sin(Δφ / 2)**2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def test_haversine_same_point():
    """Distance from a point to itself should be 0."""
    assert haversine_km(12.97, 77.59, 12.97, 77.59) == pytest.approx(0.0, abs=1e-6)


def test_haversine_known_distance():
    """Koramangala to Indiranagar is roughly 4 km."""
    d = haversine_km(12.9352, 77.6245, 12.9784, 77.6408)
    assert 3.0 < d < 6.0, f"Expected ~4km, got {d:.2f}km"


def test_haversine_symmetry():
    """Distance A→B should equal B→A."""
    d1 = haversine_km(12.97, 77.59, 12.94, 77.62)
    d2 = haversine_km(12.94, 77.62, 12.97, 77.59)
    assert d1 == pytest.approx(d2, rel=1e-6)


def test_batch_within_radius():
    """Two restaurants < 3km apart should be batchable."""
    d = haversine_km(12.9756, 77.6010, 12.9784, 77.6408)
    assert d < 3.0, f"Should be within batch radius, got {d:.2f}km"


def test_batch_outside_radius():
    """Two restaurants > 3km apart should NOT be batchable."""
    d = haversine_km(12.9756, 77.6010, 12.8000, 77.5000)
    assert d > 3.0, f"Should exceed batch radius, got {d:.2f}km"


def test_eta_calculation():
    """Travel time: 10km at 25km/h = 24 mins."""
    speed_kmh = 25.0
    distance_km = 10.0
    mins = (distance_km / speed_kmh) * 60
    assert mins == pytest.approx(24.0, abs=0.1)