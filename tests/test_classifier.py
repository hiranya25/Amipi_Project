"""
test_classifier.py — Unit tests for the priority rule engine.

Covers all four priority paths plus the critical DNR override-must-fire-first
behavior.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import classifier


def _computed(qty: int, last_90: float, current_stock: int) -> dict:
    """Build a minimal computed dict shaped like engine.compute()'s output."""
    return {
        "suggested_order_qty": qty,
        "_raw_last_90": last_90,
        "_raw_current_stock": current_stock,
    }


def test_dnr_override_fires_first():
    """last90=2, stock=10, qty=8 -> DNR overrides what would otherwise be High."""
    result = classifier.classify(_computed(qty=8, last_90=2, current_stock=10))
    assert result["priority"] == "Do Not Reorder"
    assert result["recommendation"] == "Do Not Reorder"


def test_dnr_does_not_fire_when_stock_below_threshold():
    """last90=4, stock=8 -> last90 > 3, so DNR should NOT fire; normal tiers apply."""
    result = classifier.classify(_computed(qty=0, last_90=4, current_stock=8))
    assert result["priority"] != "Do Not Reorder"


def test_dnr_does_not_fire_when_sales_above_threshold():
    """last90=4 (>3) fails the DNR sales condition even with high stock."""
    result = classifier.classify(_computed(qty=1, last_90=4, current_stock=20))
    assert result["priority"] != "Do Not Reorder"


def test_high_qty_threshold():
    """qty=5 -> High, when DNR conditions are not also met (last_90 > 3)."""
    result = classifier.classify(_computed(qty=5, last_90=12, current_stock=20))
    assert result["priority"] == "High"
    assert result["recommendation"] == "Reorder"


def test_high_stock_emergency():
    """stock=2, last90=10 -> High, even if suggested qty is low."""
    result = classifier.classify(_computed(qty=1, last_90=10, current_stock=2))
    assert result["priority"] == "High"
    assert result["recommendation"] == "Reorder"


def test_medium_qty_range():
    """qty=3 (within [2,4]) -> Medium, when DNR conditions are not also met."""
    result = classifier.classify(_computed(qty=3, last_90=12, current_stock=20))
    assert result["priority"] == "Medium"
    assert result["recommendation"] == "Reorder"


def test_medium_qty_range_boundaries():
    """qty=2 and qty=4 are inclusive boundaries of the Medium range."""
    assert classifier.classify(_computed(qty=2, last_90=12, current_stock=20))["priority"] == "Medium"
    assert classifier.classify(_computed(qty=4, last_90=12, current_stock=20))["priority"] == "Medium"


def test_medium_stock_plus_sales():
    """stock=3, last90=7 -> Medium via the stock+sales path."""
    result = classifier.classify(_computed(qty=1, last_90=7, current_stock=3))
    assert result["priority"] == "Medium"
    assert result["recommendation"] == "Reorder"


def test_low_default():
    """qty=1, nothing else triggers higher tiers -> Low / Monitor."""
    result = classifier.classify(_computed(qty=1, last_90=12, current_stock=20))
    assert result["priority"] == "Low"
    assert result["recommendation"] == "Monitor"


def test_low_qty_zero():
    """qty=0 with no other triggers -> Low / Monitor (stock kept below DNR threshold)."""
    result = classifier.classify(_computed(qty=0, last_90=0, current_stock=5))
    assert result["priority"] == "Low"
    assert result["recommendation"] == "Monitor"


def test_dnr_fires_for_qty_zero_with_high_stock():
    """qty=0, last_90=0, stock=20 -> this DOES satisfy the DNR override (low sales + high stock)."""
    result = classifier.classify(_computed(qty=0, last_90=0, current_stock=20))
    assert result["priority"] == "Do Not Reorder"


def test_high_takes_precedence_when_multiple_high_conditions_true():
    """
    qty=5 should be High even though the High stock-emergency condition is
    also satisfied -- verifies rule evaluation order doesn't misclassify
    when multiple High conditions are true simultaneously.
    """
    result = classifier.classify(_computed(qty=5, last_90=10, current_stock=2))
    assert result["priority"] == "High"
