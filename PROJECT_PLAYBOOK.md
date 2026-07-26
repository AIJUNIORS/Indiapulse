# IndiaPulse — Project Playbook

## End Goal

IndiaPulse is a comprehensive macro and sector intelligence platform for
Indian financial markets, combining macro-economic analysis, market cycle
analysis, sector/industry rotation, factor investing, commodities, fixed
income, valuation, momentum, and seasonality.

Rather than functioning as a stock screener, it answers questions such as:

- Which sectors are entering a strong seasonal period?
- Where are macro conditions becoming favourable?
- Which industries are strengthening?
- What is the current market cycle?
- Which asset classes deserve higher allocation?
- Which opportunities have the highest probability over the next 1–6 months?

The core objective is an **Opportunity Score** for each market segment.

## Opportunity Score

```
35% Seasonality
30% Macro Cycle
20% Momentum
15% Valuation
```

Each component is normalized to 0–100 before weighting.

## Planned Dashboards

1. **Global** — market health, cycle, fear & greed, breadth, opportunity score, risk
2. **Macro** — CPI, WPI, GDP, repo rate, forex reserves, FII/DII, bond yields, USDINR, PMI, IIP
3. **Market** — Nifty 50/100/200, Midcap, Smallcap — trend, momentum, valuation, breadth, drawdown, seasonality
4. **Sector** — IT, Banking, Auto, FMCG, Pharma, Realty, etc.
5. **Industry** — Chemicals, Logistics, Defence, Hospitals, Cement, Insurance, etc.
6. **Commodities** — Gold, Silver, Copper, Oil, Natural Gas
7. **Fixed Income** — Gov bonds, Bharat Bond, SDL, Corporate bonds
8. **Opportunity** — flagship ranking across every category

## Core Calculations

- **Trend** — SMA 20/50/100/200, EMA → Bullish / Neutral / Bearish
- **Momentum** — RSI, MACD, Rate of Change, ADX, Relative Strength
- **Volatility** — ATR, historical volatility, rolling volatility, beta, max drawdown
- **Breadth** — advance/decline ratio, new highs/lows, % above moving averages, participation
- **Valuation** — PE, PB, dividend yield, earnings yield, sector premiums
- **Macro Cycle** — Recovery → Expansion → Peak → Slowdown → Recession → Recovery

## Seasonality (Core Feature)

Seasonality is the largest single component of the Opportunity Score (35%).
The approach:

1. Analyze monthly returns across many years of history.
2. Remove outliers (configurable std-dev threshold) to reduce distortion.
3. Build a normalized Seasonal Index per calendar month.
4. Identify historically strong/weak periods per sector and industry.

This gives a forward-looking seasonal probability rather than relying on
recent price action alone. Implemented in `backend/analytics/seasonality.py`.

## Data Pipeline

```
Universe → Download Engine → Raw Historical Data → Indicators →
Analytics → Scores → Dashboard
```

## Milestones

| # | Milestone                | Status |
|---|---------------------------|--------|
| 1 | Project Setup             | ✅ Complete |
| 2 | Universe Generator        | ✅ Complete |
| 3 | Backend Foundation        | ✅ Complete |
| 4 | Download Engine           | ✅ Complete (retry, validation, incremental) |
| 5 | Indicator Engine          | ✅ Complete |
| 6 | Analytics Engine          | ✅ Complete |
| 7 | Scoring Engine            | ✅ Complete |
| 8 | Dashboard                 | ✅ Complete (static, no server) |
| 9 | Automation                | 🟡 In Progress |

### Milestone 2 — Universe Generator

Implemented broad market, sectors, industries, themes, factors, fixed income,
commodities, and macro universes as CSVs (`scripts/populate_universe.py`).

### Milestone 3 — Backend Foundation

`config.py`, `sources.py`, `download.py`, `logger.py`, plus analytics and
indicator module scaffolding. The provider registry maps asset classes to
providers (`backend/sources.py`).

### Milestone 4 — Download Engine

Reads universe CSVs, merges & de-duplicates symbols, selects a provider,
downloads historical data via `yfinance`, validates it, and saves one CSV per
symbol. Includes retry logic with backoff, logging integration, and
incremental ("only fetch missing days") updates.

## Remaining Roadmap

### Phase 5 — Indicator Engine ✅
Moving averages, RSI, MACD, ATR, returns, relative strength.

### Phase 6 — Analytics Engine ✅
Trend, momentum, risk, volatility, breadth, valuation (interface only —
needs a fundamentals provider), seasonality, macro cycle (interface only —
needs a live macro connector).

### Phase 7 — Scoring Engine ✅
Opportunity Score, Risk Score. Conviction/Confidence scores are a natural
extension once valuation and macro cycle are backed by live data.

### Phase 8 — Dashboard ✅
Static HTML/JS dashboards for Market, Macro, Sector, Industry, Commodities,
and Opportunity ranking, reading directly from exported JSON.

### Phase 9 — Automation 🟡
Next steps:
- Schedule `backend/update.py` (cron / GitHub Actions / Task Scheduler) to
  refresh data, recompute analytics, and re-export JSON on a cadence.
- Build the RBI / MOSPI / GSTN macro connector so `analytics/cycle.py`
  receives live growth/inflation/rate inputs instead of placeholders.
- Add a fundamentals provider (PE/PB/dividend yield) so
  `analytics/valuation.py` produces real scores.
- Generate alerts/reports from the Opportunity board.

## Long-Term Vision

IndiaPulse is designed to evolve from a data aggregation tool into a
decision-support system for strategic asset allocation — identifying where
capital is most likely to be rewarded across sectors, industries,
commodities, and macro themes, by integrating historical seasonality,
current macro conditions, technical momentum, valuation, and risk into a
unified framework.
