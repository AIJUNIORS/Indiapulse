# IndiaPulse

**IndiaPulse** is a macro and sector intelligence platform for Indian financial
markets. Instead of screening individual stocks, it answers questions like:

- Which sectors are entering a strong seasonal period?
- Where are macro conditions becoming favourable?
- What is the current market cycle?
- Which asset classes deserve higher allocation over the next 1–6 months?

Every sector, industry, theme, factor, commodity and fixed-income segment gets
an **Opportunity Score (0–100)**, weighted:

```
35% Seasonality
30% Macro Cycle
20% Momentum
15% Valuation
```

See `PROJECT_PLAYBOOK.md` for the full vision, milestone status, and roadmap.

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/<you>/indiapulse.git
cd indiapulse
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Generate the universe

The universe CSVs under `data/universe/` are already committed, but you can
regenerate them any time:

```bash
python3 scripts/populate_universe.py
```

### 3. Download historical data & compute analytics

```bash
python -m backend.main --download
```

This will:
1. Read every universe CSV and merge/de-duplicate symbols.
2. Download OHLCV history via `yfinance` (retry logic + validation included).
3. Compute trend, momentum, volatility, risk, seasonality, valuation and the
   Opportunity Score for every symbol with data.
4. Export one JSON file per category into `json/` for the frontend.

For subsequent runs, use incremental mode so only new bars are fetched:

```bash
python -m backend.main --download --incremental
```

or use the dedicated update runner (intended for scheduling — see Phase 9):

```bash
python -m backend.update
```

### 4. View the dashboards

The frontend is static HTML/JS that reads directly from `json/`. Serve the
repo root with any static file server so relative fetches resolve correctly
(opening the HTML files directly via `file://` will block `fetch()` in most
browsers):

```bash
python3 -m http.server 8000
```

Then open:

- `http://localhost:8000/frontend/index.html` — Global dashboard
- `http://localhost:8000/frontend/markets/sectors.html` — Sector dashboard
- `http://localhost:8000/frontend/analytics/compare.html` — Opportunity ranking

---

## Repository Layout

```
backend/
  analytics/        Trend, momentum, volatility, breadth, valuation,
                     macro cycle, seasonality, risk, opportunity scoring,
                     validation, and per-symbol summary assembly
  indicators/        SMA/EMA, RSI, MACD, ATR, returns
  config.py          Loads config.yaml, exposes paths & settings
  download.py        Universe merge + yfinance download engine (retry,
                     validation, incremental updates)
  export.py          Writes analytics results to json/ for the frontend
  logger.py           Central logging setup
  main.py            Pipeline orchestrator (Universe -> Download ->
                     Indicators -> Analytics -> Scores -> Dashboard)
  sources.py         Provider registry & symbol->ticker mapping
  update.py          Incremental update runner (for scheduling)
  utils.py           Shared helpers

data/
  universe/          Generated CSV universes (broad market, sectors,
                     industries, themes, factors, fixed income,
                     commodities, macro)
  historical/         One CSV per symbol (git-ignored, generated locally)

frontend/            Static HTML/JS dashboards (no build step, no server
                     framework — just fetch() against json/)

json/                 Exported analytics, one file per category
                     (git-ignored, generated locally)

scripts/
  populate_universe.py   Milestone 2 universe generator

config.yaml           Central configuration (paths, weights, indicator
                     periods, retry settings)
```

---

## Current Status

| Milestone                     | Status         |
|--------------------------------|----------------|
| 1 — Project Setup              | ✅ Complete     |
| 2 — Universe Generator         | ✅ Complete     |
| 3 — Backend Foundation         | ✅ Complete     |
| 4 — Download Engine            | ✅ Complete     |
| 5 — Indicator Engine           | ✅ Complete     |
| 6 — Analytics Engine           | ✅ Complete     |
| 7 — Scoring Engine             | ✅ Complete     |
| 8 — Dashboard (static)         | ✅ Complete     |
| 9 — Automation / Scheduling    | 🟡 In Progress  |

Notes on what's still a placeholder:

- **Valuation** (`analytics/valuation.py`) needs a fundamentals data provider
  (PE/PB/dividend yield per index) — currently returns a neutral 50 score
  until that's wired in.
- **Macro Cycle** (`analytics/cycle.py`) takes `growth_trend`,
  `inflation_trend`, and `rate_direction` as inputs; `backend/main.py`
  currently passes neutral placeholders until a live RBI/MOSPI/GSTN
  connector is built (macro series are defined in `data/universe/macro.csv`
  and registered under a `manual` provider in `sources.py`).
- Some `YFINANCE_SYMBOL_MAP` entries in `sources.py` are best-effort proxies
  (commented inline) — verify tickers against Yahoo Finance before relying on
  them for anything beyond development/testing.

---

## Running Tests

```bash
pip install pytest
pytest tests/
```

(`tests/` currently contains scaffolding — add coverage as analytics logic
evolves.)

---

## License

MIT — see `LICENSE`.
