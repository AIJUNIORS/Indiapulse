# Addendum: repo layout (supersedes architecture doc §5's `backend/factors/`, `backend/scoring/` subfolders)

Every module built across this project -- the 5 originals and the 9 added
since -- uses **flat, top-level imports**: `from trend import compute_trend`,
`import price_cache`, `from data_hierarchy import resolve_all`, etc. None of
them use package-qualified imports (`from factors.trend import ...`) or sit
behind an `__init__.py`.

Architecture doc §5 shows a nested layout (`backend/factors/{trend,...}.py`,
`backend/scoring/{opportunity_score,weights.json}`). Adopting that layout
as-drawn, with these files unchanged, breaks every import at runtime.

Resolution: **keep it flat.** Lower risk than converting ~14 files to
package-relative imports and adding `__init__.py` scaffolding, and every
module's own `if __name__=='__main__'` smoke test already assumes flat
`sys.path.insert(0, '.')` resolution. Actual repo layout:

```
backend/
  sources.py, data_hierarchy.py, composite_builder.py, fx.py, data_fetch.py, price_cache.py
  trend.py, position.py, cycle.py, volatility.py, seasonality.py, technicals.py, momentum_signals.py
  structure_score.py, business_score.py, business_calendar_data.py, opportunity_score.py
  serializer.py, quality_guard.py, pipeline.py
  test_price_cache.py, test_factors.py
  requirements.txt
frontend/
  indiapulse-mockup.html
data/state/
  cycle_state.json          # committed, cycle.py's 3-week confirmation lag
.github/workflows/
  refresh-daily.yml, refresh-weekly.yml, business-intelligence.yml, validate-quarterly.yml
```

Two other doc/implementation mismatches, noted for the same reason (doc
describes something the code doesn't do -- flagged rather than silently
left inconsistent):

- **`scoring/weights.json`** (§5): not externalized. `opportunity_score.py`
  and `structure_score.py` both hardcode their blend weights as Python
  constants (`WEIGHTS = {...}`) at module level, same pattern as every
  other tunable constant in this codebase (e.g. `trend.py`'s slope_score
  constant). Externalizing to JSON would be a small follow-up if runtime
  (not code-change) weight tuning is ever needed -- not done here.
- **`composite_weights.json`** (§4, §6): not used. `composite_builder.py`
  recomputes the full quarterly rebalance from raw constituent history on
  every run -- stateless by design, nothing to persist between runs. The
  doc describes a state file the implementation never needed.
