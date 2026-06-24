"""
loader.py — Reads and validates the two source CSV files.

Responsibilities
-----------------
1. Read data/inventory_sales.csv and data/event_multipliers.csv with pandas.
2. Validate that all required columns are present (schema check at startup).
   Missing columns -> SchemaError, abort before any processing.
3. Clean row-level problems WITHOUT ever modifying the source files:
   - Null/NaN values -> log a warning, skip that row.
   - Non-numeric values in numeric fields -> attempt pd.to_numeric coercion;
     if that fails, skip the row with a warning.
   - event_name not found in event_multipliers.csv -> log an error, skip
     the affected row.

The loader never writes back to the input CSVs. It returns clean, in-memory
records ready for the computation engine.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

import config

logger = logging.getLogger("inventory_tool.loader")

NUMERIC_FIELDS = ["current_stock", "on_order", "last_90_day_sales", "days_until_event"]


class SchemaError(Exception):
    """Raised when a required column is missing from an input CSV."""


def _build_rename_map(
    columns: list[str], aliases: dict[str, list[str]]
) -> dict[str, str]:
    """
    Map actual CSV column names (case-insensitive) to canonical field names
    using the alias table in config.py. Returns {actual_column: canonical_name}.
    """
    lower_to_actual = {c.strip().lower(): c for c in columns}
    rename_map: dict[str, str] = {}

    for canonical, alias_list in aliases.items():
        for alias in alias_list:
            actual = lower_to_actual.get(alias.strip().lower())
            if actual is not None:
                rename_map[actual] = canonical
                break

    return rename_map


def _validate_schema(
    df: pd.DataFrame, required_columns: list[str], aliases: dict[str, list[str]], source_name: str
) -> pd.DataFrame:
    """Rename columns to canonical names and confirm all required ones exist."""
    rename_map = _build_rename_map(list(df.columns), aliases)
    df = df.rename(columns=rename_map)

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise SchemaError(
            f"{source_name} is missing required column(s): {', '.join(missing)}. "
            f"Found columns: {list(df.columns)}. "
            f"If your file uses different header names, add an alias in "
            f"config.py — do not rename the source CSV."
        )

    return df


def load_event_multipliers(path: Path | None = None) -> dict[str, float]:
    """
    Load event_multipliers.csv into a dict: {event_name: multiplier}.

    Raises SchemaError if required columns are missing.
    """
    path = path or config.EVENT_MULTIPLIERS_CSV

    if not path.exists():
        raise SchemaError(f"Event multipliers file not found: {path}")

    df = pd.read_csv(path)
    df = _validate_schema(
        df, config.REQUIRED_EVENT_COLUMNS, config.EVENT_MULTIPLIERS_COLUMN_ALIASES, str(path)
    )

    multipliers: dict[str, float] = {}
    for idx, row in df.iterrows():
        event_name = row.get("event_name")
        mult_raw = row.get("event_multiplier")

        if pd.isna(event_name):
            logger.warning("Row %s in %s: missing event_name, skipping.", idx, path.name)
            continue

        mult = pd.to_numeric(mult_raw, errors="coerce")
        if pd.isna(mult):
            logger.warning(
                "Row %s in %s: non-numeric event_multiplier %r for event '%s', skipping.",
                idx, path.name, mult_raw, event_name,
            )
            continue

        multipliers[str(event_name).strip()] = float(mult)

    if not multipliers:
        raise SchemaError(
            f"No valid rows found in {path}. Check that the file has data beyond the header."
        )

    return multipliers


def load_inventory_sales(path: Path | None = None) -> pd.DataFrame:
    """
    Load inventory_sales.csv with schema validation.

    Row-level cleaning happens here:
    - Coerces numeric fields with pd.to_numeric (NaN on failure).
    - Drops rows with NaN in any required numeric field or missing style_number,
      logging a warning identifying the offending style_number when available.

    Returns a cleaned DataFrame. Does NOT do the event_multiplier lookup —
    that join happens in main.py / engine layer so a missing event can be
    logged with full context.
    """
    path = path or config.INVENTORY_SALES_CSV

    if not path.exists():
        raise SchemaError(f"Inventory & sales file not found: {path}")

    df = pd.read_csv(path)
    df = _validate_schema(
        df, config.REQUIRED_INVENTORY_COLUMNS, config.INVENTORY_SALES_COLUMN_ALIASES, str(path)
    )

    # Coerce numeric columns; bad values become NaN rather than raising.
    for field in NUMERIC_FIELDS:
        df[field] = pd.to_numeric(df[field], errors="coerce")

    clean_rows: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        style = row.get("style_number")
        style_label = style if pd.notna(style) else f"<row {idx}>"

        if pd.isna(style) or str(style).strip() == "":
            logger.warning("Row %s: missing style_number, skipping row.", idx)
            continue

        if pd.isna(row.get("event_name")) or str(row.get("event_name")).strip() == "":
            logger.warning("Style %s: missing event_name, skipping row.", style_label)
            continue

        missing_numeric = [f for f in NUMERIC_FIELDS if pd.isna(row.get(f))]
        if missing_numeric:
            logger.warning(
                "Style %s: invalid/missing numeric value(s) in %s, skipping row.",
                style_label, ", ".join(missing_numeric),
            )
            continue

        clean_rows.append(
            {
                "style_number": str(style).strip(),
                "current_stock": row["current_stock"],
                "on_order": row["on_order"],
                "last_90_day_sales": row["last_90_day_sales"],
                "days_until_event": row["days_until_event"],
                "event_name": str(row["event_name"]).strip(),
            }
        )

    if not clean_rows:
        raise SchemaError(
            f"No usable rows remained in {path} after validation. "
            f"Check the warnings above for details."
        )

    return pd.DataFrame(clean_rows)
