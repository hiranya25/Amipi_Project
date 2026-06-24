# Inventory Recommendation Tool

An event-aware restocking recommendation tool for jewelry inventory. It computes
how many units of each SKU to reorder ahead of a trade show or holiday event,
classifies each SKU into a priority tier, and generates a short, jewelry-retail
business justification for each recommendation.

Built for **AMIPI Project 3** — Inventory Recommendation Tool.

---

## ✅ Assignment Deliverables Checklist

- **Runs locally with clear setup:** See [Setup](#setup) & [Web Interface](#web-interface-frontend) sections.
- **Uses provided CSV files:** Data is loaded cleanly via `pandas` in `loader.py` without mutating source files.
- **3+ Sample Outputs:** Four fully formatted JSON samples are provided in the [Sample Outputs](#sample-outputs) section.
- **Validation & Error Handling:** Comprehensive edge-case handling documented in [Validation](#validation--error-handling). Missing columns, invalid files, and API failures are handled gracefully without python tracebacks.
- **AI vs Deterministic boundary:** Explicitly documented below. The rule engine calculates all quantities/priorities entirely deterministically. AI is exclusively restricted to generating the string in the `reason` field.
- **No hard-coded answers:** Fully dynamic, reusable logic engine. Adding a new row mathematically computes its values based solely on formulas, not lookup tables.

---

## How it works

The tool is a linear, single-pass pipeline. Each stage has one responsibility
and can be tested independently:

```
CLI (main.py)
   -> loader.py        reads + validates the two input CSVs
   -> engine.py        5 deterministic formulas (pure math, no side effects)
   -> classifier.py    priority rule engine (DNR override evaluated first)
   -> ai_reason.py      Groq LLaMA 3.3 70B generates the "reason" field
   -> formatter.py     console table + JSON/CSV export
```

### Where AI is used vs. where deterministic rules are used

This is the most important design decision in the project, so it's worth
stating plainly:

- **Everything that produces a number is 100% deterministic.** `available_inventory`,
  `monthly_sales_rate`, `projected_demand_until_event`, `recommended_stock_needed`,
  and `suggested_order_qty` all come from fixed formulas in `engine.py`. The
  `priority` and `recommendation` fields come from a fixed rule table in
  `classifier.py`. None of this is ever touched by the AI model — the same
  input will always produce the same numbers and the same priority, every time.
- **AI is used for exactly one field: `reason`.** Once the quantity and
  priority have already been decided, `ai_reason.py` asks Groq's LLaMA 3.3 70B
  model to phrase a one-sentence, jewelry-retail-flavored explanation of a
  decision that has already been made. The model never sees the raw CSVs and
  has no path to influence the order quantity or priority — it only writes
  the sentence that explains them.

If the AI call fails or is disabled (`--no-ai`), the deterministic part of the
output is completely unaffected — only the `reason` field falls back to a
template string.

---

## Required calculations (implemented exactly as specified)

```
available_inventory          = current_stock + on_order
monthly_sales_rate            = last_90_day_sales / 3
projected_demand_until_event  = monthly_sales_rate * (days_until_event / 30)
recommended_stock_needed      = projected_demand_until_event * event_multiplier
suggested_order_qty           = max(0, round(recommended_stock_needed - available_inventory))
```

No rounding happens until the final `suggested_order_qty` step — all
intermediate values carry full floating-point precision internally, and are
only rounded to 2 decimal places for display/output.

## Priority rules (evaluated in this exact order)

| Order | Priority | Condition | Recommendation |
|---|---|---|---|
| 1st (**override**) | **Do Not Reorder** | `last_90_day_sales <= 3 AND current_stock >= 8` | Do Not Reorder |
| 2nd | **High** | `suggested_order_qty >= 5` OR (`current_stock <= 2 AND last_90_day_sales >= 10`) | Reorder |
| 3rd | **Medium** | `suggested_order_qty` in `[2, 4]` OR (`current_stock <= 3 AND last_90_day_sales >= 6`) | Reorder |
| 4th (default) | **Low** | `suggested_order_qty` is 0 or 1 | Monitor |

**"Do Not Reorder" is an override.** It is checked first; if it matches, the
tool short-circuits immediately and never evaluates High/Medium/Low for that
row — even if the quantity math alone would otherwise suggest a high-priority
reorder.

---

## Project structure

```
inventory-recommendation-tool/
├── main.py                   # CLI entry point
├── web.py                    # Web Interface entry point (Flask)
├── web_static/               # Frontend CSS, JS, HTML assets
├── config.py                 # Constants, env vars, column-name mapping
├── loader.py                 # CSV ingestion + schema/row validation
├── engine.py                 # Deterministic computation (the 5 formulas)
├── classifier.py             # Priority + recommendation rules
├── ai_reason.py              # Groq API integration (reason field only)
├── formatter.py              # Console table, JSON, CSV output
│
├── data/
│   ├── inventory_sales.csv    # READ-ONLY input — sample data included
│   └── event_multipliers.csv  # READ-ONLY input — sample data included
│
├── output/
│   ├── recommendations.json   # Generated on --output-json
│   └── recommendations.csv    # Generated on --output-csv
│
├── tests/
│   ├── test_engine.py         # Unit tests for all 5 formulas
│   ├── test_classifier.py     # Unit tests for all 4 priority paths + DNR override
│   └── test_integration.py    # End-to-end pipeline test with a mocked Groq client
│
├── .env.example                # Template for your own .env
├── requirements.txt
└── README.md
```

> **About the data:** `data/inventory_sales.csv` and `data/event_multipliers.csv`
> are the real files provided with the assignment — 20 SKUs across five events
> (JCK Vegas, JIS Miami, Mother's Day, Valentine's Day, Holiday Season). Note
> that the real files use slightly different headers than the spec's literal
> example (`event` instead of `event_name`, plus extra descriptive columns like
> `category`, `metal`, `stone_type`, `last_30_day_sales`, and `season` that
> aren't used by the calculations). The loader handles this through the
> column-alias table in `config.py` — no part of the source CSVs was edited or
> renamed to make this work.

---

## Setup

1. **Clone/unzip the project and navigate into it.**

2. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate        # Windows: .c
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Get a free Groq API key** at [console.groq.com](https://console.groq.com)
   — no credit card required.

5. **Create your `.env` file:**
   ```bash
   cp .env.example .env
   # then edit .env and paste in your key:
   # GROQ_API_KEY=your_key_here
   ```

6. **Run it:**
   ```bash
   python main.py --event "JCK Vegas" --output-json --output-csv
   ```

If you don't have a Groq key yet, or just want to test the deterministic
logic, add `--no-ai` to any command and the AI call is skipped entirely in
favor of a template reason string.

### Windows Setup

```powershell
# Create and activate virtual environment
py -m venv venv
.\venv\Scripts\Activate.ps1

# If activation is blocked, run this first:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install -r requirements.txt

# Create .env file
Copy-Item .env.example .env
```

Add your Groq key to `.env`:

```env
GROQ_API_KEY=your_key_here
```

Run without an API key:

```powershell
python main.py --event "JCK Vegas" --no-ai
```

Run the web interface:

```powershell
python web.py
```

Open `http://127.0.0.1:5000`.


---

## CLI usage

```bash
# Basic run — processes all SKUs tagged with the given event
python3 main.py --event "JCK Vegas"

# Export both JSON and CSV
python3 main.py --event "JCK Vegas" --output-json --output-csv

# Process a single SKU for debugging
python3 main.py --event "JCK Vegas" --style B401400-14WVS

# Skip AI entirely — deterministic only (no API key needed)
python3 main.py --event "JCK Vegas" --no-ai

# Point at different CSV files (without modifying the originals)
python3 main.py --event "JCK Vegas" --inventory-csv path/to/file.csv --events-csv path/to/other.csv

# Verbose / debug logging
python3 main.py --event "JCK Vegas" --no-ai -v

# Help
python3 main.py --help
```

---

## Web Interface (Frontend)

This project also includes a complete, high-performance web interface!

To run the web app:
```bash
python3 web.py
```
Then, open your browser to **http://localhost:5000**.
The web interface features:
- A drag-and-drop Command Center
- Slide-over panel detailing the full mathematical breakdown and AI reason
- Real-time priority color coding
- Export buttons for JSON and CSV directly from the browser

---

## Sample outputs

These are real outputs from a live `--no-ai` run against the **actual provided
data files** (`python main.py --event "JCK Vegas" --no-ai`). With a Groq API
key configured, the `reason` field is generated by LLaMA 3.3 70B instead of
the fallback templates shown here — the numeric fields and priority are
identical either way.

**Console table — JCK Vegas (7 SKUs tagged for this event):**

```
Style             Avail    Monthly    Proj    Mult    Rec Needed    Order  Priority    Action
--------------  -------  ---------  ------  ------  ------------  -------  ----------  --------
B401400-14WVS         7       4.67    5.44       2         10.89        4  Medium      Reorder
LB401400-14WVS        8       6.67    7.78       2         15.56        8  High        Reorder
B501200-18YRA        12       1.33    1.56       2          3.11        0  Low         Monitor
B801300-PTVS          1       2.67    3.11       2          6.22        5  High        Reorder
B778800-18REM         2       2       2.33       2          4.67        3  Medium      Reorder
B888111-18YVS         3       4.33    5.06       2         10.11        7  High        Reorder
LB888222-18WVS        8      10      11.67       2         23.33       15  High        Reorder
```

**Sample 1 — Medium priority:**

```json
{
  "style_number": "B401400-14WVS",
  "available_inventory": 7,
  "monthly_sales_rate": 4.67,
  "projected_demand_until_event": 5.44,
  "event_multiplier": 2.0,
  "recommended_stock_needed": 10.89,
  "suggested_order_qty": 4,
  "priority": "Medium",
  "recommendation": "Reorder",
  "reason": "Solid recent sales and upcoming event lift support a moderate replenishment order."
}
```

**Sample 2 — High priority (near-zero stock + strong sell-through):**

```json
{
  "style_number": "B801300-PTVS",
  "available_inventory": 1,
  "monthly_sales_rate": 2.67,
  "projected_demand_until_event": 3.11,
  "event_multiplier": 2.0,
  "recommended_stock_needed": 6.22,
  "suggested_order_qty": 5,
  "priority": "High",
  "recommendation": "Reorder",
  "reason": "Strong sell-through and event demand point to an urgent restock to avoid a stockout."
}
```

**Sample 3 — Low priority (sufficient coverage, no order needed):**

```json
{
  "style_number": "B501200-18YRA",
  "available_inventory": 12,
  "monthly_sales_rate": 1.33,
  "projected_demand_until_event": 1.56,
  "event_multiplier": 2.0,
  "recommended_stock_needed": 3.11,
  "suggested_order_qty": 0,
  "priority": "Low",
  "recommendation": "Monitor",
  "reason": "Current coverage looks adequate for now; monitor sell-through as the event approaches."
}
```

**Sample 4 — Do Not Reorder (from the JIS Miami event — `B998877-14RS`,
stock=15, last_90_day_sales=1):**

```json
{
  "style_number": "B998877-14RS",
  "available_inventory": 15,
  "monthly_sales_rate": 0.33,
  "projected_demand_until_event": 0.67,
  "event_multiplier": 1.5,
  "recommended_stock_needed": 1.0,
  "suggested_order_qty": 0,
  "priority": "Do Not Reorder",
  "recommendation": "Do Not Reorder",
  "reason": "Slow 90-day velocity against healthy on-hand stock supports holding off on replenishment for now."
}
```

The full run (all 7 JCK Vegas SKUs) is saved at `output/recommendations.json`
and `output/recommendations.csv`. The other four events in the data
(`JIS Miami`, `Mother's Day`, `Valentine's Day`, `Holiday Season`) can be run
the same way, e.g. `python3 main.py --event "Holiday Season" --no-ai`.

---

## Validation & error handling

The tool never crashes the whole batch over one bad row, and it never
modifies the source CSVs:

| Scenario | What happens |
|---|---|
| Missing required column in either CSV | Aborts immediately at startup with a clear `[SCHEMA ERROR]` naming the missing column — before any rows are processed. |
| Missing/blank `style_number` or `event_name` in a row | That row is skipped with a logged warning; the rest of the batch continues. |
| Non-numeric value in a numeric field | Tool attempts to coerce it; if that fails, the row is skipped with a warning identifying the style number and field. |
| `event_name` not found in `event_multipliers.csv`, or the `--event` you passed doesn't match any row | Clear `[ERROR]` message listing the events that *are* available. |
| `days_until_event == 0` | Valid case — projected demand and suggested order both come out to 0, no error. |
| `last_90_day_sales == 0` | Valid case — no recent sales is not an error; the DNR rule may legitimately fire. |
| Groq API rate limit / network error | Exponential backoff retry (1s, 2s, 4s) for up to 3 attempts, then a deterministic fallback reason string — the numeric fields are never affected. |
| `GROQ_API_KEY` missing while AI mode is on | Clear `[CONFIG ERROR]` suggesting either setting the key or re-running with `--no-ai`. |
| Output directory not writable | Caught and reported with the exact path and a permission hint, instead of a raw stack trace. |

You can see all of this exercised directly — try, for example:

```bash
python main.py --event "Some Event That Does Not Exist" --no-ai
python main.py --event "JCK Vegas" --inventory-csv does/not/exist.csv --no-ai
```

---

## Running the tests

```bash
pytest tests/ -v
```

23 tests, all passing:

- **`test_engine.py`** — the standard worked example, zero-sales edge case,
  event-today edge case, the never-negative guard, and invalid-input handling.
- **`test_classifier.py`** — all four priority tiers, both conditions within
  each tier, and — critically — that the DNR override fires *before* and
  *instead of* what would otherwise be a High-priority classification.
- **`test_integration.py`** — a full loader → engine → classifier → AI-reason
  run with a **mocked** Groq client (`unittest.mock`). No test ever makes a
  live API call, so the suite is fast, free, and fully deterministic.

```
============================== 23 passed in 0.30s ==============================
```

---

## Notes on code quality

- Every module has a single responsibility and can be imported/tested on its own.
- `engine.py` and `classifier.py` are pure functions with no side effects and
  no I/O — they're trivial to unit test and trivial to reason about.
- Nothing is hard-coded row-by-row. The same five-line formula chain and the
  same four-rule classifier run against every SKU in the file; adding a new
  SKU to the CSV requires zero code changes.
- Type hints and docstrings are used throughout. Column names are resolved
  through an alias table in `config.py` rather than hard-coded strings
  scattered through the codebase, so a future header rename in the real data
  files only requires a one-line config change.
