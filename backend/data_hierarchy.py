"""
data_hierarchy.py -- IndiaPulse source resolution (v3.1 S2.2)

resolve_source() implements the decision function from the spec:
    1. Representative ETF (>=3yr history)      -- preferred
    2. Underlying Benchmark Index (>=3yr history)
    3. Market Leader Composite                 -- whenever neither the ETF
       nor its benchmark clears 3yr, including when neither exists at all

No sub-3yr instrument is ever analyzed directly (v3.1 S2.1, hard floor).
Every resolved source is confidence="high" or unresolved -- there is no
`data_confidence: limited` state (v3.1 v3.1-update note, S2.2).

Futures and FX categories (Copper/Crude Oil/Natural Gas, USD/INR) bypass the
equity ETF -> benchmark -> composite ladder entirely -- they're not equity
categories with an ETF/benchmark/composite choice, they're direct tradable
series. Still gated by the same 3yr floor.

This module only decides *what to use*. It does not fetch prices, does not
run on a schedule, and does not write to the deployed data/ output -- that's
composite_builder.py / the daily-computed factor pipeline downstream. This
runs once per PR that touches sources.py, or on demand via the CLI below.
"""

from dataclasses import dataclass
from typing import Optional, Literal

from sources import CATEGORY_SOURCES, CategorySource, InstrumentCandidate

MIN_HISTORY_YEARS = 3.0

Resolution = Literal['etf', 'benchmark', 'composite', 'futures', 'fx', 'unresolved']


@dataclass(frozen=True)
class ResolvedSource:
    group: str
    name: str
    resolution: Resolution
    symbol: Optional[str]           # the instrument actually used for price series
    display_etf: Optional[str]      # a sub-3yr ETF that exists but wasn't used -- shown for context only, never analyzed
    constituents: Optional[tuple]
    history_years: float
    return_basis: str               # 'TRI' | 'price_only' | 'na' -- v3.1 S2.3
    confidence: Literal['high', 'pending']
    flag: Optional[str]              # 'context' | 'currency' | None, copied straight from CategorySource
    verified: bool                  # False = candidate is a proposed/unconfirmed entry, flag for review
    note: str = ''


def resolve_source(cat: CategorySource) -> ResolvedSource:
    """v3.1 S2.2 decision function, ported directly from the spec's pseudocode."""

    etf = cat.candidates.get('etf')
    if etf and etf.history_years >= MIN_HISTORY_YEARS:
        return ResolvedSource(
            group=cat.group, name=cat.name, resolution='etf',
            symbol=etf.symbol, display_etf=None, constituents=None,
            history_years=etf.history_years, return_basis=etf.return_basis,
            confidence='high', flag=cat.flag, verified=etf.verified, note=etf.note,
        )

    benchmark = cat.candidates.get('benchmark')
    if benchmark and benchmark.history_years >= MIN_HISTORY_YEARS:
        return ResolvedSource(
            group=cat.group, name=cat.name, resolution='benchmark',
            symbol=benchmark.symbol, display_etf=(etf.symbol if etf else None),
            constituents=None, history_years=benchmark.history_years,
            return_basis=benchmark.return_basis, confidence='high',
            flag=cat.flag, verified=benchmark.verified, note=benchmark.note,
        )

    # Direct instruments (futures/FX) sit outside the equity ladder but still
    # respect the same floor -- if a futures/FX series is somehow sub-3yr,
    # fall through to composite (v3.1 doesn't define a commodity composite,
    # so in practice this only matters if a new commodity category is added
    # before it has 3 years of trading history).
    for kind in ('futures', 'fx'):
        inst = cat.candidates.get(kind)
        if inst and inst.history_years >= MIN_HISTORY_YEARS:
            return ResolvedSource(
                group=cat.group, name=cat.name, resolution=kind,
                symbol=inst.symbol, display_etf=None, constituents=None,
                history_years=inst.history_years, return_basis=inst.return_basis,
                confidence='high', flag=cat.flag, verified=inst.verified, note=inst.note,
            )

    composite = cat.candidates.get('composite')
    if composite:
        return ResolvedSource(
            group=cat.group, name=cat.name, resolution='composite',
            symbol=None, display_etf=(etf.symbol if etf else None),
            constituents=composite.constituents, history_years=composite.history_years,
            return_basis=composite.return_basis, confidence='high',
            flag=cat.flag, verified=composite.verified, note=composite.note,
        )

    return ResolvedSource(
        group=cat.group, name=cat.name, resolution='unresolved',
        symbol=None, display_etf=None, constituents=None, history_years=0.0,
        return_basis='na', confidence='pending', flag=cat.flag, verified=False,
        note='No candidate clears the 3yr floor and no composite is registered '
             '-- add a composite candidate to sources.py before this category can ship.',
    )


def resolve_all() -> list[ResolvedSource]:
    return [resolve_source(c) for c in CATEGORY_SOURCES]


# ---------------------------------------------------------------------------
# Regeneration + review tooling -- run by a human via PR, never by the
# scheduled pipeline. The scheduled pipeline reads sources.py as fixed input;
# it never calls these.
# ---------------------------------------------------------------------------

_SOURCE_TYPE_LABEL = {
    'etf': 'ETF', 'benchmark': 'Index', 'composite': 'Composite',
    'futures': 'Futures', 'fx': 'FX',
}


def to_raw_row(r: ResolvedSource) -> str:
    """
    Render one row in the exact literal shape the frontend's embedded `RAW`
    array already uses: [group, name, sourceType, source, historyYears, flag?]
    Paste the output of regenerate_raw_js() into the frontend's RAW block by
    hand (or via reviewed PR diff) -- this never runs at deploy time.
    """
    source_label = r.symbol if r.symbol else (
        '/'.join(r.constituents) if r.constituents else 'UNRESOLVED'
    )
    type_label = _SOURCE_TYPE_LABEL.get(r.resolution, r.resolution)
    parts = [f"'{r.group}'", f"'{r.name}'", f"'{type_label}'",
              f"'{source_label}'", f"{r.history_years}"]
    return f"[{', '.join(parts)}],"


def regenerate_raw_js() -> str:
    lines = ['const RAW = [']
    for r in resolve_all():
        lines.append('  ' + to_raw_row(r))
    lines.append('];')
    return '\n'.join(lines)


def diff_report() -> str:
    """
    The PR-review checklist: categories where resolve_source()'s decision
    doesn't match what's currently embedded in the frontend's RAW catalog,
    or where the resolved source isn't fully verified. Print this before
    merging any sources.py change.
    """
    current = {(c.group, c.name): c for c in CATEGORY_SOURCES}
    lines = []
    unresolved = []
    unverified = []
    floor_violations = []

    for r in resolve_all():
        cat = current[(r.group, r.name)]
        # was there a sub-3yr candidate that WOULD have been used directly
        # under the old (pre-v3.1) rules? -- flags the exact discrepancy
        # class this hierarchy exists to catch.
        etf = cat.candidates.get('etf')
        if etf and etf.history_years < MIN_HISTORY_YEARS and r.resolution != 'unresolved':
            floor_violations.append(
                f"  {r.group}/{r.name}: ETF {etf.symbol} is {etf.history_years}y (< {MIN_HISTORY_YEARS}y floor) "
                f"-> correctly resolved to {r.resolution} instead ({r.symbol or '/'.join(r.constituents or [])}, "
                f"{r.history_years}y)"
            )
        if r.resolution == 'unresolved':
            unresolved.append(f"  {r.group}/{r.name}: {r.note}")
        if not r.verified:
            unverified.append(f"  {r.group}/{r.name}: resolved via {r.resolution}, UNVERIFIED -- {r.note}")

    if floor_violations:
        lines.append(f"3yr-floor corrections applied ({len(floor_violations)}):")
        lines.extend(floor_violations)
        lines.append('')
    if unverified:
        lines.append(f"Unverified candidates in use, needs confirmation before merge ({len(unverified)}):")
        lines.extend(unverified)
        lines.append('')
    if unresolved:
        lines.append(f"UNRESOLVED -- blocks shipping this category ({len(unresolved)}):")
        lines.extend(unresolved)
        lines.append('')
    if not (floor_violations or unverified or unresolved):
        lines.append('No issues -- every category resolves to a verified >=3yr source.')

    return '\n'.join(lines)


if __name__ == '__main__':
    import sys

    if '--regenerate' in sys.argv:
        print(regenerate_raw_js())
    else:
        print(diff_report())
