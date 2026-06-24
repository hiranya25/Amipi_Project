"""
config.py — Centralized configuration for the Inventory Recommendation Tool.

Holds environment loading, API/model constants, file paths, and the
column-name mapping layer. If the real-world CSV files ever use different
header names than the ones specified in the data contract, remap them here
ONLY — never modify the source CSV files themselves.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
load_dotenv()  # reads .env in project root if present

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

INVENTORY_SALES_CSV = DATA_DIR / "inventory_sales.csv"
EVENT_MULTIPLIERS_CSV = DATA_DIR / "event_multipliers.csv"

OUTPUT_JSON_PATH = OUTPUT_DIR / "recommendations.json"
OUTPUT_CSV_PATH = OUTPUT_DIR / "recommendations.csv"

# ---------------------------------------------------------------------------
# Required input columns (the data contract).
# If a real-world CSV uses different header text, map the alias here instead
# of editing the source file. Keys are the canonical names used throughout
# the codebase; values are lists of acceptable header aliases (case-insensitive).
# ---------------------------------------------------------------------------
INVENTORY_SALES_COLUMN_ALIASES = {
    "style_number": ["style_number", "style", "sku", "style number"],
    "current_stock": ["current_stock", "stock", "on_hand", "current stock"],
    "on_order": ["on_order", "onorder", "on order"],
    "last_90_day_sales": [
        "last_90_day_sales",
        "last_90_days_sales",
        "sales_90_day",
        "last 90 day sales",
    ],
    "days_until_event": ["days_until_event", "days_to_event", "days until event"],
    "event_name": ["event_name", "event", "event name"],
}

EVENT_MULTIPLIERS_COLUMN_ALIASES = {
    "event_name": ["event_name", "event", "event name"],
    "event_multiplier": ["event_multiplier", "multiplier", "event multiplier"],
}

REQUIRED_INVENTORY_COLUMNS = list(INVENTORY_SALES_COLUMN_ALIASES.keys())
REQUIRED_EVENT_COLUMNS = list(EVENT_MULTIPLIERS_COLUMN_ALIASES.keys())

# ---------------------------------------------------------------------------
# Output field order (matches the assignment's required output fields)
# ---------------------------------------------------------------------------
OUTPUT_FIELDS = [
    "style_number",
    "available_inventory",
    "monthly_sales_rate",
    "projected_demand_until_event",
    "event_multiplier",
    "recommended_stock_needed",
    "suggested_order_qty",
    "priority",
    "recommendation",
    "reason",
]

# ---------------------------------------------------------------------------
# AI generation settings
# ---------------------------------------------------------------------------
AI_MAX_TOKENS = 80
AI_TEMPERATURE = 0.4
AI_MAX_RETRIES = 3

FALLBACK_REASON_TEMPLATES = {
    "Do Not Reorder": (
        "Slow 90-day velocity against healthy on-hand stock supports holding "
        "off on replenishment for now."
    ),
    "High": (
        "Strong sell-through and event demand point to an urgent restock to "
        "avoid a stockout."
    ),
    "Medium": (
        "Solid recent sales and upcoming event lift support a moderate "
        "replenishment order."
    ),
    "Low": (
        "Current coverage looks adequate for now; monitor sell-through as the "
        "event approaches."
    ),
}


class ConfigError(Exception):
    """Raised for unrecoverable configuration problems (e.g. missing API key)."""
