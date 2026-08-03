"""
quality_guard.py -- v3.1 architecture doc S8: "assert every category in RAW
has a corresponding entry in computed.json before deploy; abort deploy on
mismatch." A category silently missing from the feed would render as
null/'Insufficient History' everywhere, which is SAFE for the user but
should still fail the CI build loudly so it gets fixed rather than shipped
quietly and forgotten.

This module only decides pass/fail + why -- pipeline.py is responsible for
actually stopping the deploy (non-zero exit) when check_all() reports
failures.
"""

from typing import Optional

from data_hierarchy import ResolvedSource


def check_completeness(resolved: list[ResolvedSource], computed: dict) -> list[str]:
    """Every (group, name) in resolve_all()'s output must have a key in computed.json,
    even unresolved categories (they should still get a null-filled entry upstream in
    pipeline.py, not be dropped outright -- a dropped key is what this catches)."""
    issues = []
    for r in resolved:
        entry = computed.get(r.group, {}).get(r.name)
        if entry is None:
            issues.append(f"MISSING computed.json entry: {r.group}/{r.name}")
    return issues


def check_score_ranges(computed: dict) -> list[str]:
    """Sanity bounds -- catches an upstream formula bug (e.g. an unclamped blend)
    before it ships a nonsensical number to the frontend."""
    issues = []
    for group, categories in computed.items():
        for name, entry in categories.items():
            for field in ('structure', 'opportunity', 'posPct', 'rsi'):
                value = entry.get(field)
                if value is not None and not (0 <= value <= 100):
                    issues.append(f"OUT OF RANGE {field}={value}: {group}/{name}")
            for field in ('fundamental', 'contra'):
                value = entry.get(field)
                if value is not None and not (1 <= value <= 5):
                    issues.append(f"OUT OF RANGE {field}={value}: {group}/{name}")
    return issues


def check_seasonality_grid_shape(resolved: list[ResolvedSource], seasonality: dict,
                                   expected_months: int = 12, expected_lookbacks: int = 6) -> list[str]:
    """Catches a partial grid (e.g. only current month serialized) before it ships --
    computedSeasonState()/monthReturnRank() on the frontend silently mis-rank if any
    month is missing, without throwing, so this has to be caught here, not at runtime."""
    issues = []
    for r in resolved:
        if r.resolution == 'unresolved':
            continue
        entry = seasonality.get(r.group, {}).get(r.name)
        if entry is None:
            issues.append(f"MISSING seasonality.json entry: {r.group}/{r.name}")
            continue
        if len(entry) != expected_months:
            issues.append(f"INCOMPLETE seasonality grid ({len(entry)}/{expected_months} months): {r.group}/{r.name}")
            continue
        for month, lookback_grid in entry.items():
            if len(lookback_grid) != expected_lookbacks:
                issues.append(f"INCOMPLETE seasonality lookbacks for {month} "
                               f"({len(lookback_grid)}/{expected_lookbacks}): {r.group}/{r.name}")
    return issues


def check_unverified_sources(resolved: list[ResolvedSource]) -> list[str]:
    """
    Non-blocking: surfaces any category currently resolving to an
    unverified candidate (verified=False -- a proposed/unconfirmed entry,
    per ResolvedSource's own field comment). data_hierarchy.py's
    diff_report() already catches this at PR-review time; this check
    exists so it ALSO shows up in every CI run's output, not just when
    someone remembers to run diff_report() by hand before merging a
    sources.py change -- a category can drift from verified to unverified
    (or vice versa) without anyone touching sources.py directly, e.g. if a
    verified candidate's history_years drops below the 3yr floor and
    resolve_source() falls through to an unverified composite candidate.
    Returned as warnings, not issues -- shipping on an unverified source is
    a real judgment call for a human, not something quality_guard should
    unilaterally block deploy over.
    """
    warnings = []
    for r in resolved:
        if r.resolution != 'unresolved' and not r.verified:
            warnings.append(f"UNVERIFIED source in use: {r.group}/{r.name} "
                             f"(resolved via {r.resolution}, {r.symbol or '/'.join(r.constituents or [])}) -- {r.note}")
    return warnings


def check_all(resolved: list[ResolvedSource], computed: dict, seasonality: dict) -> dict:
    """Runs every check; returns {'ok': bool, 'issues': [...], 'warnings': [...]}.
    pipeline.py should exit non-zero and print issues if ok is False -- last-good
    deploy stays live. Warnings are printed too but never block deploy."""
    issues = (
        check_completeness(resolved, computed)
        + check_score_ranges(computed)
        + check_seasonality_grid_shape(resolved, seasonality)
    )
    warnings = check_unverified_sources(resolved)
    return {'ok': len(issues) == 0, 'issues': issues, 'warnings': warnings}


if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')
    from data_hierarchy import resolve_all

    resolved = resolve_all()
    # Smoke test against an intentionally incomplete payload
    fake_computed = {r.group: {} for r in resolved}
    fake_seasonality = {}
    result = check_all(resolved, fake_computed, fake_seasonality)
    print(f"ok={result['ok']}, {len(result['issues'])} issues (expect many -- this is a smoke test)")
    for issue in result['issues'][:10]:
        print(f"  {issue}")
