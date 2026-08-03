"""
factors/momentum_signals.py -- arrow, accel, exhaustion.

IMPORTANT CAVEAT, read before trusting these numbers: unlike every other
field in this codebase (rsi, smi, atrPct, trendPct, pivotDist all had an
inline comment in the mockup saying exactly what real thing they stand in
for), these three fields have NO definition anywhere in the mockup or the
architecture doc -- they were pure rnd() with no explanatory comment. What
follows is this module's best inference from how the fields are actually
CONSUMED (grep the mockup: arrow drives the Trend row's glyph + Top Movers
rail + Business Calendar chip color; accel drives the Rotation page's
"likely up/down" filters; exhaustion drives its own leaderboard + the
Rotation page's "Exhaustion" verdict) -- not a confirmed spec. Treat this
whole module as a PROPOSAL pending confirmation, same way trend.py flags
its slope_score constant, just one level more provisional: those constants
have a real formula to tune, this module doesn't even have a confirmed
formula yet.

arrow -- direction glyph, one of the frontend's 5 ARROWS buckets
    (down/downright/side/upright/up). Inferred as a direct re-bucketing of
    trend.py's own continuous raw_score (same 5-way split trend.py already
    uses for TREND_LABELS) -- i.e. arrow is a visual restatement of `trend`,
    not an independent signal. This is the simplest reading and avoids
    inventing a second trend measure that could silently disagree with the
    one already shown next to it in the drawer (see mockup line ~1579,
    where Trend's label and arrow render side by side).

accel -- momentum acceleration (2-way: down/side/up per the frontend's
    3-bucket ACCEL). Inferred as the change in trend.py's 30w EMA slope
    between the current reading and its value N weeks ago -- i.e. "is the
    trend line itself steepening or flattening," a second derivative on
    top of trend.py's existing first-derivative slope_pct_10w.

exhaustion -- move extension (4-way: None/Early/Moderate/High per EXH_LEVELS).
    Inferred as a blend of two "how stretched is this" reads that already
    exist: RSI extremity (technicals.py) and Position percentile extremity
    (position.py) -- a move deep into overbought RSI AND near the top of its
    5Y range reads as more exhausted than either alone.

None of these three should be treated as tuned or validated -- flag this
module for confirmation before it ships, more so than any other module in
this codebase.
"""

from typing import Optional

ARROW_BUCKETS = [('↓', 'down'), ('↘', 'downright'), ('→', 'side'), ('↗', 'upright'), ('↑', 'up')]
ACCEL_BUCKETS = {'down': ('↓ Decelerating', 'down'), 'side': ('→ Stable', 'side'), 'up': ('↑ Accelerating', 'up')}
EXH_LEVELS = [('None', 'none'), ('Early', 'early'), ('Moderate', 'moderate'), ('High', 'high')]

ACCEL_LOOKBACK_WEEKS = 10          # compare current 10w slope vs slope 10w ago -- same window trend.py already uses
ACCEL_FLAT_BAND_PCT = 0.5          # slope change within +-0.5pp counts as "Stable" -- tunable, no S6 data behind this number


def compute_arrow(trend_result: dict) -> Optional[tuple]:
    """Direct re-bucketing of trend.py's raw_score into the frontend's 5-way ARROWS -- see module docstring."""
    if trend_result.get('insufficient_history'):
        return None
    idx = min(4, max(0, int(trend_result['raw_score'] // 20)))
    return ARROW_BUCKETS[idx]


def compute_accel(weekly_close, slope_lookback_weeks: int = ACCEL_LOOKBACK_WEEKS) -> Optional[tuple]:
    """
    Second derivative of trend: is the 30w EMA's slope itself rising or
    falling? Recomputes the EMA locally rather than importing trend.py's
    internals, since trend.py doesn't currently expose slope at two points
    in time -- only the latest slope_pct_10w.
    """
    ema30 = weekly_close.ewm(span=30, adjust=False).mean()
    if len(ema30) < slope_lookback_weeks * 2 + 1:
        return None

    def _slope_at(end_idx: int) -> float:
        start_idx = end_idx - slope_lookback_weeks
        if ema30.iloc[start_idx] == 0:
            return 0.0
        return (ema30.iloc[end_idx] - ema30.iloc[start_idx]) / ema30.iloc[start_idx] * 100

    current_slope = _slope_at(-1)
    prior_slope = _slope_at(-1 - slope_lookback_weeks)
    delta = current_slope - prior_slope

    if delta > ACCEL_FLAT_BAND_PCT:
        return ACCEL_BUCKETS['up']
    if delta < -ACCEL_FLAT_BAND_PCT:
        return ACCEL_BUCKETS['down']
    return ACCEL_BUCKETS['side']


def compute_exhaustion(technicals_result: dict, position_result: dict) -> Optional[tuple]:
    """
    Blend of RSI extremity + Position percentile extremity, each mapped to
    0-100 "how stretched" reads and averaged:
      RSI: distance beyond 50 toward either extreme, i.e. |rsi-50|*2 (rsi=100 or 0 -> 100 stretched)
      Position: |percentile-50|*2, same shape
    Bucketed the same way as volatility.py's percentile-based bucket_volatility().
    """
    if technicals_result.get('insufficient_history') or position_result.get('insufficient_history'):
        return None
    rsi = technicals_result.get('rsi')
    percentile = position_result.get('percentile')
    if rsi is None or percentile is None:
        return None

    rsi_stretch = abs(rsi - 50) * 2
    position_stretch = abs(percentile - 50) * 2
    stretch = (rsi_stretch + position_stretch) / 2

    if stretch >= 85:
        return EXH_LEVELS[3]   # High
    if stretch >= 60:
        return EXH_LEVELS[2]   # Moderate
    if stretch >= 30:
        return EXH_LEVELS[1]   # Early
    return EXH_LEVELS[0]       # None


if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')
    import price_cache
    from data_hierarchy import resolve_all
    from composite_builder import get_category_series
    from trend import compute_trend
    from position import compute_position
    from technicals import compute_technicals

    resolved = [r for r in resolve_all() if r.resolution != 'unresolved'][:5]
    for r in resolved:
        try:
            series = get_category_series(r)
            trend_result = compute_trend(series['close'])
            position_result = compute_position(series['close'])
            technicals_result = compute_technicals(series)
            arrow = compute_arrow(trend_result)
            accel = compute_accel(series['close'].resample('W-FRI').last().dropna())
            exhaustion = compute_exhaustion(technicals_result, position_result)
            print(f"{r.group}/{r.name}: arrow={arrow} accel={accel} exhaustion={exhaustion}")
        except Exception as e:
            print(f"{r.group}/{r.name}: SKIP -- {e}")
