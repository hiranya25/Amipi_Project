"""
engine.py — Deterministic computation engine.

Pure functions, zero side-effects, zero AI calls. Implements the five
required formulas exactly as specified in the assignment:

    available_inventory          = current_stock + on_order
    monthly_sales_rate           = last_90_day_sales / 3
    projected_demand_until_event = monthly_sales_rate * (days_until_event / 30)
    recommended_stock_needed     = projected_demand_until_event * event_multiplier
    suggested_order_qty          = max(0, round(recommended_stock_needed - available_inventory))

No rounding happens until the final suggested_order_qty step — all
intermediate math is done in full floating-point precision. Display-rounded
values (2dp) are produced only in the returned dict for output purposes;
internally we keep full precision available to downstream callers via the
"_raw_*" passthrough fields.
"""

from __future__ import annotations

from typing import Any


def compute(row: dict[str, Any], event_multiplier: float) -> dict[str, Any]:
    """
    Compute all intermediate and final values for a single SKU row.

    Parameters
    ----------
    row : dict
        Must contain current_stock, on_order, last_90_day_sales,
        days_until_event (numeric, already validated by loader.py).
    event_multiplier : float
        Looked up from event_multipliers.csv for this row's event_name.

    Returns
    -------
    dict with the six computed fields (available_inventory,
    monthly_sales_rate, projected_demand_until_event, event_multiplier,
    recommended_stock_needed, suggested_order_qty) plus raw passthrough
    values the classifier needs (_raw_last_90, _raw_current_stock).

    Raises
    ------
    ValueError
        If required fields cannot be coerced to the expected numeric types.
        Callers (main.py) should catch this per-row and skip/log.
    """
    try:
        current_stock = int(row["current_stock"])
        on_order = int(row["on_order"])
        last_90 = float(row["last_90_day_sales"])
        days_until_event = float(row["days_until_event"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid numeric input for row {row.get('style_number')}: {exc}") from exc

    if current_stock < 0 or on_order < 0:
        raise ValueError(
            f"Negative stock/on_order is not valid for row {row.get('style_number')}."
        )
    if days_until_event < 0:
        raise ValueError(
            f"days_until_event cannot be negative for row {row.get('style_number')}."
        )

    # Step 1: total inventory already in hand or inbound.
    available_inventory = current_stock + on_order

    # Step 2: average monthly sell-through over the trailing 90 days.
    # No guard needed for division by zero here — we divide BY 3 (a constant),
    # not by last_90, so last_90 == 0 is simply a valid "no recent sales" case.
    monthly_sales_rate = last_90 / 3

    # Step 3: expected demand between now and the event, scaled by the
    # number of "30-day months" remaining.
    projected_demand = monthly_sales_rate * (days_until_event / 30)

    # Step 4: demand amplified by the event's expected lift.
    recommended_stock_needed = projected_demand * event_multiplier

    # Step 5: the only rounding step. Never recommend a negative order.
    suggested_order_qty = max(0, round(recommended_stock_needed - available_inventory))

    return {
        "available_inventory": available_inventory,
        "monthly_sales_rate": round(monthly_sales_rate, 2),
        "projected_demand_until_event": round(projected_demand, 2),
        "event_multiplier": event_multiplier,
        "recommended_stock_needed": round(recommended_stock_needed, 2),
        "suggested_order_qty": suggested_order_qty,
        # Raw values passed forward for the priority classifier — these are
        # the un-rounded source numbers the priority rules key off of.
        "_raw_last_90": last_90,
        "_raw_current_stock": current_stock,
        "_raw_on_order": on_order,
        "_raw_days_until_event": days_until_event,
    }
