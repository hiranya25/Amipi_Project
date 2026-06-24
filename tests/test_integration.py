"""
test_integration.py — End-to-end pipeline test with a mocked Groq client.

CRITICAL: We never make live API calls in the test suite -- that burns
free-tier quota and makes tests non-deterministic. The Groq client is
fully mocked via unittest.mock.patch / a hand-rolled fake client object.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ai_reason
import classifier
import engine
import loader


class _FakeGroqResponse:
    """Mimics the shape of a Groq chat completion response."""

    def __init__(self, text: str):
        message = MagicMock()
        message.content = text
        choice = MagicMock()
        choice.message = message
        self.choices = [choice]


class _FakeGroqClient:
    """Mocked Groq client — never touches the network."""

    def __init__(self, response_text: str = "Reorder recommended based on strong sell-through."):
        self.response_text = response_text
        self.chat = MagicMock()
        self.chat.completions.create = MagicMock(
            return_value=_FakeGroqResponse(self.response_text)
        )


def test_full_pipeline_single_record_with_mocked_ai():
    """Run loader -> engine -> classifier -> ai_reason end-to-end for one row."""
    event_multipliers = {"JCK Vegas": 2.0}
    row = {
        "style_number": "B401400-14WVS",
        "current_stock": 3,
        "on_order": 4,
        "last_90_day_sales": 14,
        "days_until_event": 35,
        "event_name": "JCK Vegas",
    }

    computed = engine.compute(row, event_multiplier=event_multipliers["JCK Vegas"])
    tier = classifier.classify(computed)

    record = {
        "style_number": row["style_number"],
        "event_name": row["event_name"],
        **computed,
        **tier,
    }

    fake_client = _FakeGroqClient("Strong JCK Vegas demand supports a 4-unit replenishment.")
    record["reason"] = ai_reason.generate_reason(record, client=fake_client)

    # Deterministic fields match the spec example exactly.
    assert record["available_inventory"] == 7
    assert record["monthly_sales_rate"] == 4.67
    assert record["projected_demand_until_event"] == 5.44
    assert record["recommended_stock_needed"] == 10.89
    assert record["suggested_order_qty"] == 4
    assert record["priority"] == "Medium"
    assert record["recommendation"] == "Reorder"

    # AI field came from the mocked client, not a live call.
    assert "JCK Vegas" in record["reason"]
    fake_client.chat.completions.create.assert_called_once()


def test_pipeline_falls_back_when_ai_call_fails():
    """If the (mocked) Groq client raises on every retry, we get a fallback string, not a crash."""
    row = {
        "style_number": "N105000-14WVSYG",
        "current_stock": 14,
        "on_order": 0,
        "last_90_day_sales": 2,
        "days_until_event": 35,
        "event_name": "JCK Vegas",
    }
    computed = engine.compute(row, event_multiplier=2.0)
    tier = classifier.classify(computed)
    record = {"style_number": row["style_number"], "event_name": row["event_name"], **computed, **tier}

    assert record["priority"] == "Do Not Reorder"

    failing_client = MagicMock()
    failing_client.chat.completions.create.side_effect = Exception("simulated network error")

    reason = ai_reason.generate_reason(record, client=failing_client, retries=1)

    assert isinstance(reason, str)
    assert len(reason) > 0
    # Should not have raised, and should be the DNR fallback template.
    assert "velocity" in reason.lower() or "stock" in reason.lower()


def test_loader_reads_provided_csvs():
    """Sanity check that the real, provided data/*.csv files parse cleanly end-to-end."""
    event_multipliers = loader.load_event_multipliers()
    inventory_df = loader.load_inventory_sales()

    assert "JCK Vegas" in event_multipliers
    assert len(inventory_df) > 0
    assert "style_number" in inventory_df.columns
