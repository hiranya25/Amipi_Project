"""
formatter.py — Renders final records as a console table, JSON file, and/or
CSV file.

Handles the "Output directory not writable" error scenario gracefully by
catching OSError and printing an actionable message with the path and a
permission hint, rather than crashing with a raw traceback.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any

from tabulate import tabulate

import config

logger = logging.getLogger("inventory_tool.formatter")


def to_console_table(records: list[dict[str, Any]]) -> str:
    """Render records as a human-readable console table."""
    if not records:
        return "(no records to display)"

    headers = [
        "Style", "Avail", "Monthly", "Proj", "Mult",
        "Rec Needed", "Order", "Priority", "Action",
    ]
    rows = [
        [
            r["style_number"],
            r["available_inventory"],
            r["monthly_sales_rate"],
            r["projected_demand_until_event"],
            r["event_multiplier"],
            r["recommended_stock_needed"],
            r["suggested_order_qty"],
            r["priority"],
            r["recommendation"],
        ]
        for r in records
    ]
    return tabulate(rows, headers=headers, tablefmt="simple")


def _ensure_output_dir(path: Path) -> bool:
    """Create the output directory if needed. Returns False (with a logged
    message) if it cannot be created or written to."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        return True
    except OSError as exc:
        print(
            f"\n[ERROR] Could not create output directory '{path.parent}': {exc}\n"
            f"  -> Check that the path exists and that you have write permission.\n"
            f"  -> On Linux/macOS try: chmod u+w {path.parent}\n"
        )
        return False


def write_json(records: list[dict[str, Any]], path: Path | None = None) -> bool:
    """Write records to a JSON file. Returns True on success, False on failure."""
    path = path or config.OUTPUT_JSON_PATH

    if not _ensure_output_dir(path):
        return False

    try:
        # Drop internal "_raw_*" passthrough fields — keep only the 10
        # required output fields, in the required order.
        clean = [{field: r[field] for field in config.OUTPUT_FIELDS} for r in records]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(clean, f, indent=2, ensure_ascii=False)
        return True
    except OSError as exc:
        print(
            f"\n[ERROR] Could not write JSON output to '{path}': {exc}\n"
            f"  -> Check directory permissions and available disk space.\n"
        )
        return False


def write_csv(records: list[dict[str, Any]], path: Path | None = None) -> bool:
    """Write records to a CSV file. Returns True on success, False on failure."""
    path = path or config.OUTPUT_CSV_PATH

    if not _ensure_output_dir(path):
        return False

    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=config.OUTPUT_FIELDS)
            writer.writeheader()
            for r in records:
                writer.writerow({field: r[field] for field in config.OUTPUT_FIELDS})
        return True
    except OSError as exc:
        print(
            f"\n[ERROR] Could not write CSV output to '{path}': {exc}\n"
            f"  -> Check directory permissions and available disk space.\n"
        )
        return False
