#!/usr/bin/env python3
"""
main.py — CLI entry point for the Inventory Recommendation Tool.

Pipeline:
    CLI args -> loader.py -> engine.py -> classifier.py -> ai_reason.py -> formatter.py

Usage
-----
    python main.py --event "JCK Vegas"
    python main.py --event "JCK Vegas" --output-json --output-csv
    python main.py --event "JCK Vegas" --style B401400-14WVS
    python main.py --event "JCK Vegas" --no-ai
    python main.py --help
"""

from __future__ import annotations

import argparse
import logging
import sys

import ai_reason
import classifier
import config
import engine
import formatter
import loader

logger = logging.getLogger("inventory_tool")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=(
            "Event-aware jewelry inventory restocking recommendation tool. "
            "Computes deterministic reorder quantities, classifies each SKU "
            "by priority, and generates a jewelry-retail business reason "
            "for each recommendation."
        ),
    )
    parser.add_argument(
        "--event",
        required=True,
        help="Name of the target event to plan against (must match an "
        "event_name in data/event_multipliers.csv exactly), e.g. 'JCK Vegas'.",
    )
    parser.add_argument(
        "--style",
        default=None,
        help="Process a single style_number only (useful for debugging).",
    )
    parser.add_argument(
        "--output-json",
        action="store_true",
        help=f"Write results to {config.OUTPUT_JSON_PATH}",
    )
    parser.add_argument(
        "--output-csv",
        action="store_true",
        help=f"Write results to {config.OUTPUT_CSV_PATH}",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Skip the Groq AI call entirely and use deterministic fallback "
        "reason templates instead. Useful for testing or when no API key "
        "is configured.",
    )
    parser.add_argument(
        "--inventory-csv",
        default=None,
        help="Override path to inventory_sales.csv (default: data/inventory_sales.csv).",
    )
    parser.add_argument(
        "--events-csv",
        default=None,
        help="Override path to event_multipliers.csv (default: data/event_multipliers.csv).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug-level logging.",
    )
    return parser.parse_args(argv)


def configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s | %(name)s | %(message)s",
    )


def run(args: argparse.Namespace) -> int:
    # ---- 1. Load + validate input data --------------------------------
    try:
        event_multipliers = loader.load_event_multipliers(
            args.events_csv and __import__("pathlib").Path(args.events_csv)
        )
        inventory_df = loader.load_inventory_sales(
            args.inventory_csv and __import__("pathlib").Path(args.inventory_csv)
        )
    except loader.SchemaError as exc:
        print(f"\n[SCHEMA ERROR] {exc}\n")
        return 1

    if args.event not in event_multipliers:
        available = ", ".join(sorted(event_multipliers.keys()))
        print(
            f"\n[ERROR] Event '{args.event}' was not found in "
            f"event_multipliers.csv.\nAvailable events: {available}\n"
        )
        return 1

    event_multiplier = event_multipliers[args.event]

    rows = inventory_df[inventory_df["event_name"] == args.event]
    if args.style:
        rows = rows[rows["style_number"] == args.style]
        if rows.empty:
            print(
                f"\n[ERROR] Style '{args.style}' was not found for event "
                f"'{args.event}' in inventory_sales.csv.\n"
            )
            return 1
    if rows.empty:
        print(f"\n[ERROR] No rows found for event '{args.event}' in inventory_sales.csv.\n")
        return 1

    # ---- 2 & 3. Compute + classify each row -----------------------------
    records: list[dict] = []
    for _, row in rows.iterrows():
        row_dict = row.to_dict()
        try:
            computed = engine.compute(row_dict, event_multiplier)
        except ValueError as exc:
            logger.warning("Skipping style %s: %s", row_dict.get("style_number"), exc)
            continue

        tier = classifier.classify(computed)

        record = {
            "style_number": row_dict["style_number"],
            "event_name": row_dict["event_name"],
            **computed,
            **tier,
        }
        records.append(record)

    if not records:
        print("\n[ERROR] No valid records were produced. Nothing to recommend.\n")
        return 1

    # ---- 4. AI reason generation -----------------------------------------
    groq_client = None
    if not args.no_ai:
        try:
            from groq import Groq

            if not config.GROQ_API_KEY:
                raise config.ConfigError(
                    "GROQ_API_KEY is not set. Add it to your .env file "
                    "(see .env.example), or re-run with --no-ai."
                )
            groq_client = Groq(api_key=config.GROQ_API_KEY)
        except config.ConfigError as exc:
            print(f"\n[CONFIG ERROR] {exc}\n")
            return 1
        except ImportError:
            print(
                "\n[ERROR] The 'groq' package is not installed. Run "
                "'pip install -r requirements.txt', or re-run with --no-ai.\n"
            )
            return 1

    for record in records:
        if args.no_ai:
            record["reason"] = config.FALLBACK_REASON_TEMPLATES.get(
                record["priority"], "Recommendation generated from current sales and stock data."
            )
        else:
            record["reason"] = ai_reason.generate_reason(record, client=groq_client)

    # ---- 5. Output formatting --------------------------------------------
    print()
    print(formatter.to_console_table(records))
    print()

    if args.output_json:
        if formatter.write_json(records):
            print(f"JSON written to {config.OUTPUT_JSON_PATH}")
    if args.output_csv:
        if formatter.write_csv(records):
            print(f"CSV written to {config.OUTPUT_CSV_PATH}")

    if not args.output_json and not args.output_csv:
        print("(Tip: pass --output-json and/or --output-csv to save these results to a file.)")

    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
