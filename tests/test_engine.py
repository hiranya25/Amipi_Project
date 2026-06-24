"""
test_engine.py — Unit tests for the deterministic computation engine.

Covers: the spec example, zero sales, event-today, excess inventory
(never-negative guard), and a general standard computation case.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import engine


def test_standard_computation():
    """stock=3, on_order=4, last90=14, days=35, mult=2.0 -> matches spec example."""
    row = {
        "style_number": "B401400-14WVS",
        "current_stock": 3,
        "on_order": 4,
        "last_90_day_sales": 14,
        "days_until_event": 35,
    }
    result = engine.compute(row, event_multiplier=2.0)

    assert result["available_inventory"] == 7
    assert result["monthly_sales_rate"] == pytest.approx(4.67, abs=0.01)
    assert result["projected_demand_until_event"] == pytest.approx(5.44, abs=0.01)
    assert result["recommended_stock_needed"] == pytest.approx(10.89, abs=0.01)
    assert result["suggested_order_qty"] == 4


def test_matches_spec_example_exactly():
    """The exact example from the assignment spec document."""
    row = {
        "style_number": "B401400-14WVS",
        "current_stock": 3,
        "on_order": 4,
        "last_90_day_sales": 14,
        "days_until_event": 35,
    }
    result = engine.compute(row, event_multiplier=2.0)

    assert result["available_inventory"] == 7
    assert result["monthly_sales_rate"] == 4.67
    assert result["projected_demand_until_event"] == 5.44
    assert result["event_multiplier"] == 2.0
    assert result["recommended_stock_needed"] == 10.89
    assert result["suggested_order_qty"] == 4
    # Per spec: priority should be Medium, recommendation Reorder.
    # (Verified together with classifier in test_classifier.py /
    # test_integration.py — engine.py itself does not assign priority.)


def test_zero_sales_no_recent_activity():
    """last_90_day_sales = 0 is a valid case — no recent sales, not an error."""
    row = {
        "style_number": "R220150-18WVS3",
        "current_stock": 0,
        "on_order": 0,
        "last_90_day_sales": 0,
        "days_until_event": 35,
    }
    result = engine.compute(row, event_multiplier=2.0)

    assert result["monthly_sales_rate"] == 0
    assert result["suggested_order_qty"] == 0


def test_event_today():
    """days_until_event = 0 is valid — projected demand and order qty are 0."""
    row = {
        "style_number": "R220200-PLATVS2",
        "current_stock": 3,
        "on_order": 0,
        "last_90_day_sales": 6,
        "days_until_event": 0,
    }
    result = engine.compute(row, event_multiplier=2.0)

    assert result["projected_demand_until_event"] == 0
    assert result["suggested_order_qty"] == 0


def test_excess_inventory_never_negative():
    """When available inventory far exceeds recommended stock, order qty floors at 0."""
    row = {
        "style_number": "N105000-14WVSYG",
        "current_stock": 50,
        "on_order": 20,
        "last_90_day_sales": 1,
        "days_until_event": 35,
    }
    result = engine.compute(row, event_multiplier=1.5)

    assert result["recommended_stock_needed"] < result["available_inventory"]
    assert result["suggested_order_qty"] == 0


def test_negative_stock_raises():
    row = {
        "style_number": "BAD-001",
        "current_stock": -1,
        "on_order": 0,
        "last_90_day_sales": 5,
        "days_until_event": 30,
    }
    with pytest.raises(ValueError):
        engine.compute(row, event_multiplier=1.0)


def test_negative_days_until_event_raises():
    row = {
        "style_number": "BAD-002",
        "current_stock": 5,
        "on_order": 0,
        "last_90_day_sales": 5,
        "days_until_event": -10,
    }
    with pytest.raises(ValueError):
        engine.compute(row, event_multiplier=1.0)


def test_non_numeric_input_raises():
    row = {
        "style_number": "BAD-003",
        "current_stock": "not-a-number",
        "on_order": 0,
        "last_90_day_sales": 5,
        "days_until_event": 30,
    }
    with pytest.raises(ValueError):
        engine.compute(row, event_multiplier=1.0)
