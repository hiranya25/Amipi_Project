"""
ai_reason.py — Generates the natural-language "reason" field via Groq's
LLaMA 3.3 70B model.

AI / Deterministic boundary
----------------------------
This is the ONLY module in the pipeline that calls an LLM. Every quantity,
priority, and recommendation has already been finalized by engine.py and
classifier.py before this module ever runs. The AI is used exclusively to
phrase a short, jewelry-retail-flavored business justification for a
decision that was already made deterministically — it never influences the
numbers themselves.

If the Groq API is unavailable (missing key, rate limit, network error),
generate_reason() falls back to a template string from config.py rather
than crashing the whole batch.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import config

logger = logging.getLogger("inventory_tool.ai_reason")

SYSTEM_PROMPT = """You are a senior jewelry buyer with 15 years of experience in diamond and fine jewelry retail.
You write concise, professional restock recommendations — one sentence, 15-25 words — in the voice of a buying director presenting to a merchandise team.

Use jewelry-retail vocabulary where appropriate:
carry depth, turn rate, sell-through velocity, JCK demand, trade show lift, holiday replenishment, fast movers, dead stock.

Rules:
- One sentence only. No bullet points. No preamble.
- Be specific: reference the event, the sales rate, or the stock level.
- Do Not Reorder items should warn about slow velocity or excess stock.
- High priority items should convey urgency."""


def build_prompt(record: dict[str, Any]) -> str:
    """Build the per-SKU user prompt fed to the model alongside SYSTEM_PROMPT."""
    return (
        f"Style: {record['style_number']}\n"
        f"Event: {record['event_name']} in {record['_raw_days_until_event']:.0f} days\n"
        f"Sales last 90 days: {record['_raw_last_90']} units "
        f"({record['monthly_sales_rate']} units/month)\n"
        f"Current stock: {record['_raw_current_stock']} | On order: {record['_raw_on_order']}\n"
        f"Available inventory: {record['available_inventory']}\n"
        f"Event demand multiplier: {record['event_multiplier']}x\n"
        f"Recommended stock needed: {record['recommended_stock_needed']}\n"
        f"Suggested order qty: {record['suggested_order_qty']}\n"
        f"Priority: {record['priority']} | Action: {record['recommendation']}\n\n"
        "Write the one-sentence business reason for this recommendation."
    )


def _fallback_reason(record: dict[str, Any], error: str | None = None) -> str:
    """Deterministic fallback text used when the Groq API cannot be reached."""
    template = config.FALLBACK_REASON_TEMPLATES.get(
        record.get("priority", ""), "Recommendation generated from current sales and stock data."
    )
    if error:
        logger.warning("AI reason unavailable for %s: %s", record.get("style_number"), error)
    return template


def generate_reason(
    record: dict[str, Any],
    client: Any = None,
    retries: int = config.AI_MAX_RETRIES,
) -> str:
    """
    Call Groq's chat completion endpoint to generate the business reason.

    Parameters
    ----------
    record : dict
        Fully computed + classified record for one SKU (output of engine +
        classifier, plus style_number/event_name/raw fields).
    client : groq.Groq, optional
        Pass an existing client (real or mocked) to avoid re-instantiating
        per call. If None, a new client is created from config.GROQ_API_KEY.
    retries : int
        Number of attempts before falling back to a template string.

    Returns
    -------
    The generated (or fallback) reason string. Never raises — callers can
    rely on always getting a usable string back.
    """
    if client is None:
        try:
            from groq import Groq  # imported lazily so --no-ai mode works without the package

            if not config.GROQ_API_KEY:
                raise config.ConfigError(
                    "GROQ_API_KEY is not set. Add it to your .env file, or run with --no-ai."
                )
            client = Groq(api_key=config.GROQ_API_KEY)
        except config.ConfigError:
            raise
        except Exception as exc:  # pragma: no cover - import/setup failure
            return _fallback_reason(record, error=str(exc))

    last_error: str | None = None
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_prompt(record)},
                ],
                max_tokens=config.AI_MAX_TOKENS,
                temperature=config.AI_TEMPERATURE,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:  # broad: network, auth, rate-limit, SDK errors
            last_error = str(exc)
            if attempt < retries - 1:
                time.sleep(2**attempt)  # exponential backoff: 1s, 2s, 4s
                continue
            return _fallback_reason(record, error=last_error)

    return _fallback_reason(record, error=last_error)  # pragma: no cover - defensive
