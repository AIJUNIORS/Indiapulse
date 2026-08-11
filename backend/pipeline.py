"""
pipeline.py -- v3.1 architecture doc S4, step 7: orchestrates steps 1-9 for
every resolved category and writes dist/data/*.json.

Order matters for two reasons already established by the individual
modules: (a) cycle.py's state must be loaded ONCE and saved ONCE across
the whole run, not per-category, to avoid partial-write races if the run
is interrupted mid-way (cycle.py's own module docstring); (b) structure_score
and opportunity_score both depend on trend/position/cycle/volatility
already being computed for that category, so per-category ordering is
fixed: trend -> position -> volatility -> cycle -> technicals -> structure
-> business -> seasonality/annual -> opportunity.

Curated Business Calendar: NOT ported into backend form yet (see
business_score.py's module docstring -- it's a data-entry task, separate
from this pipeline's logic). This module tries to import it and degrades
to "no business coverage for anyone" if it's absent, rather than crashing
the whole run over missing curated content -- every category still gets a
structure+seasonality-only opportunity score in that case.

Context/currency flag: ResolvedSource now carries CategorySource.flag
through (data_hierarchy.py patched), so opportunity_score.py correctly
nulls out context/currency instruments (India VIX, USD/INR, etc.), matching
the frontend's own `flag==='context' ? null : structure` line.
"""

import sys
from datetime import date
from pathlib import Path

import price_cache
from data_hierarchy import resolve_all
from composite_builder import get_category_series
from trend import compute_trend
from position import compute_position
from volatility import compute_volatility
from cycle import compute_cycle, load_state, save_state
from technicals import compute_technicals
from momentum_signals import compute_arrow, compute_accel, compute_exhaustion
from structure_score import compute_structure
from business_score import compute_effective_business_score
from seasonality import compute_seasonality_score
from opportunity_score import compute_opportunity
from serializer import build_computed_entry, build_seasonality_grid, build_annual_grid, write_json_files, _nested_set
from quality_guard import check_all

try:
    from business_calendar_data import BUSINESS_CALENDAR   # not yet ported -- see module docstring
except ImportError:
    BUSINESS_CALENDAR = {}
    print("WARNING: business_calendar_data.BUSINESS_CALENDAR not found -- "
          "every category will run with no business-score coverage this run.")

OUTPUT_DIR = Path('dist/data')


def run(current_date: date = None) -> int:
    current_date = current_date or date.today()
    current_month_idx = current_date.month - 1

    resolved = resolve_all()
    cycle_state = load_state()   # loaded once, per cycle.py's own docstring

    computed: dict = {}
    seasonality: dict = {}
    annual: dict = {}

    for r in resolved:
        if r.resolution == 'unresolved':
            # No series to compute on. quality_guard.py's own contract (see its
            # check_completeness docstring) requires every resolved category to
            # have a computed.json entry, null-filled if unresolved -- an absent
            # key is indistinguishable from a crash/bug and blocks deploy. The
            # frontend already treats absent-key and null-field identically
            # (indiapulse-mockup.html: `COMPUTED_DATA[group]?.[name] ?? {}`),
            # so null-filling here is purely to satisfy quality_guard, with no
            # frontend behavior change.
            _nested_set(computed, r.group, r.name, {
                'structure': None, 'fundamental': None, 'contra': None,
                'trend': None, 'cycle': None, 'vol': None, 'opportunity': None,
                'rsi': None, 'smi': None, 'atrPct': None, 'trendPct': None,
                'pivotDist': None, 'posPct': None, 'arrow': None,
                'accel': None, 'exhaustion': None,
            })
            continue
        try:
            series = get_category_series(r)
            close = series['close']

            trend_result = compute_trend(close)
            position_result = compute_position(close)
            volatility_result = compute_volatility(series)
            cycle_result = compute_cycle(r.group, r.name, trend_result, position_result, volatility_result, cycle_state)
            technicals_result = compute_technicals(series)
            structure_result = compute_structure(trend_result, position_result, cycle_result, volatility_result)
            business_result = compute_effective_business_score(r.name, current_month_idx, BUSINESS_CALENDAR)
            season_score = compute_seasonality_score(close, current_month_idx, r.history_years)

            arrow = compute_arrow(trend_result)
            accel = compute_accel(close.resample('W-FRI').last().dropna())
            exhaustion = compute_exhaustion(technicals_result, position_result)

            opportunity = compute_opportunity(
                structure_result.get('score'),
                business_result['fundamental'] if business_result else None,
                season_score['raw_score'],
                flag=r.flag,
            )

            entry = build_computed_entry(
                technicals_result, structure_result, business_result,
                trend_result, cycle_result, volatility_result, position_result, opportunity,
                arrow, accel, exhaustion,
            )
            _nested_set(computed, r.group, r.name, entry)
            _nested_set(seasonality, r.group, r.name, build_seasonality_grid(close, r.history_years))
            _nested_set(annual, r.group, r.name, build_annual_grid(close, r.history_years))

        except Exception as e:
            print(f"SKIP {r.group}/{r.name}: {e}")

    save_state(cycle_state)   # saved once, per cycle.py's own docstring

    quality = check_all(resolved, computed, seasonality)
    if quality['warnings']:
        print(f"QUALITY GUARD: {len(quality['warnings'])} warning(s) (non-blocking):")
        for warning in quality['warnings']:
            print(f"  {warning}")
    if not quality['ok']:
        print(f"QUALITY GUARD FAILED -- {len(quality['issues'])} issue(s), aborting deploy:")
        for issue in quality['issues']:
            print(f"  {issue}")
        return 1

    write_json_files(computed, seasonality, annual, out_dir=OUTPUT_DIR)
    print(f"Wrote {OUTPUT_DIR}/computed.json, seasonality.json, annual.json for {len(computed)} groups.")
    return 0


if __name__ == '__main__':
    sys.path.insert(0, '.')
    sys.exit(run())
