"""
classifier.py — Priority classification and recommendation rule engine.

Pure logic, no external dependencies, no AI. Implements the priority rules
exactly as specified, evaluated in this fixed order:

    1st (override) Do Not Reorder : last_90_day_sales <= 3 AND current_stock >= 8
    2nd            High           : suggested_order_qty >= 5
                                     OR (current_stock <= 2 AND last_90 >= 10)
    3rd            Medium         : suggested_order_qty in [2, 4]
                                     OR (current_stock <= 3 AND last_90 >= 6)
    4th (default)  Low            : suggested_order_qty is 0 or 1

CRITICAL: "Do Not Reorder" is an override. It is evaluated FIRST. If it
matches, we short-circuit immediately and never evaluate High/Medium/Low —
even if the quantity math would otherwise suggest a high-priority reorder.
"""

from __future__ import annotations

from typing import Any

PRIORITY_DO_NOT_REORDER = "Do Not Reorder"
PRIORITY_HIGH = "High"
PRIORITY_MEDIUM = "Medium"
PRIORITY_LOW = "Low"

RECOMMENDATION_REORDER = "Reorder"
RECOMMENDATION_MONITOR = "Monitor"
RECOMMENDATION_DNR = "Do Not Reorder"


def classify(computed: dict[str, Any]) -> dict[str, str]:
    """
    Determine priority tier and recommendation action for a single SKU.

    Parameters
    ----------
    computed : dict
        Output of engine.compute() — must contain suggested_order_qty,
        _raw_last_90, and _raw_current_stock.

    Returns
    -------
    dict with keys "priority" and "recommendation".
    """
    qty = computed["suggested_order_qty"]
    s90 = computed["_raw_last_90"]
    stock = computed["_raw_current_stock"]

    # ---- Override: evaluate FIRST, short-circuit if it matches ----------
    if s90 <= 3 and stock >= 8:
        return {"priority": PRIORITY_DO_NOT_REORDER, "recommendation": RECOMMENDATION_DNR}

    # ---- Tier rules, evaluated in order -----------------------------------
    if qty >= 5 or (stock <= 2 and s90 >= 10):
        return {"priority": PRIORITY_HIGH, "recommendation": RECOMMENDATION_REORDER}

    if 2 <= qty <= 4 or (stock <= 3 and s90 >= 6):
        return {"priority": PRIORITY_MEDIUM, "recommendation": RECOMMENDATION_REORDER}

    # ---- Default tier -------------------------------------------------------
    return {"priority": PRIORITY_LOW, "recommendation": RECOMMENDATION_MONITOR}
