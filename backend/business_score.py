"""
factors/business_score.py -- v3.1 S5 EffectiveBusinessScore.

Turns a category's curated Business Calendar state for the CURRENT calendar
month into the frontend's `fundamental` (1-5 stars) and `contra` (1-5
stars, `6 - fundamental` per the architecture doc's explicit definition)
fields.

Curated content itself (the actual month-by-month Strong/Peak/Normal/Weak/
Recovery states + rationale text, ~30 categories' worth) already exists,
hand-authored, in the frontend HTML's embedded `BUSINESS_CALENDAR` object.
This module does NOT re-author that content -- it's curated, training-
knowledge-only judgment calls (draft v0.2 per the frontend's own comment),
not something to regenerate programmatically. Porting it into a backend-
importable form (e.g. data/business_calendar.py, a straight structural
copy) is a data-entry task, separate from this module's logic, and still
pending -- this module is written against the SHAPE of that data
({name: {states: [12 labels], confidence: 'high'|'medium'|'low', why: [12
strings]}}), not a hardcoded copy of its content.

Categories with no curated entry (Broad Market, Market Cap, Strategy,
Global Markets, Innovation, Logistics per the frontend's own scope note)
correctly return None -- "out of scope," not a data gap, matching how the
frontend already renders '--' for these today.

Star mapping (v1 heuristic -- NOT spec'd beyond "1-5 stars" in the mockup;
tunable like every other bucketing constant in this codebase):
    Peak=5, Strong=4, Normal=3, Recovery=2, Weak=1
Recovery scores below Normal, not above Weak-but-improving -- it's still an
underperforming month, just past the trough; treating it as the SAME
severity as Weak would collapse a real distinction the calendar draws
between "still declining" and "past the bottom, not yet normal."

Confidence tapering mirrors seasonality.py's neutral-shrink precedent:
low/medium-confidence curated reads pull toward the neutral center (3)
rather than being reported at full strength, since a 'low' confidence
curated call is a considered guess, not a verified pattern.
"""

from typing import Optional

STATE_SCORES = {'Peak': 5, 'Strong': 4, 'Normal': 3, 'Recovery': 2, 'Weak': 1}
CONFIDENCE_WEIGHT = {'high': 1.0, 'medium': 0.7, 'low': 0.4}
NEUTRAL_SCORE = 3.0


def compute_effective_business_score(category_name: str, month_idx: int, calendar: dict) -> Optional[dict]:
    """
    category_name: matches the frontend's BUSINESS_CALENDAR key (category
    `name`, not `group|name` -- the curated calendar is keyed by name alone,
    same as the frontend's own `BUSINESS_CALENDAR[c.name]` lookup).
    month_idx: 0=Jan..11=Dec.
    calendar: the full curated dict, shape {name: {states, confidence, why}}.
    Returns None if this category has no curated entry -- caller (pipeline)
    should leave fundamental/contra as null, exactly like the frontend does
    today for out-of-scope categories.
    """
    entry = calendar.get(category_name)
    if entry is None:
        return None

    state = entry['states'][month_idx]
    confidence = entry.get('confidence', 'medium')
    raw_score = STATE_SCORES.get(state, 3)
    weight = CONFIDENCE_WEIGHT.get(confidence, 0.7)

    tapered = NEUTRAL_SCORE + (raw_score - NEUTRAL_SCORE) * weight
    fundamental = max(1, min(5, round(tapered)))
    contra = max(1, min(5, 6 - fundamental))

    return {
        'fundamental': fundamental,
        'contra': contra,
        'state': state,
        'confidence': confidence,
        'rationale': entry.get('why', [None] * 12)[month_idx],
    }


if __name__ == '__main__':
    # Smoke test against a tiny inline stand-in calendar -- the real
    # curated dict isn't ported into backend form yet (see module docstring).
    sample_calendar = {
        'Banking': {
            'states': ['Strong', 'Strong', 'Peak', 'Normal', 'Normal', 'Weak',
                       'Weak', 'Recovery', 'Recovery', 'Strong', 'Strong', 'Strong'],
            'confidence': 'high',
            'why': ['placeholder'] * 12,
        },
        'Metals': {
            'states': ['Normal', 'Recovery', 'Strong', 'Strong', 'Normal', 'Weak',
                       'Weak', 'Recovery', 'Normal', 'Normal', 'Recovery', 'Normal'],
            'confidence': 'low',
            'why': ['placeholder'] * 12,
        },
    }
    for name in ('Banking', 'Metals', 'Not A Category'):
        for month_idx in (0, 5, 7):
            result = compute_effective_business_score(name, month_idx, sample_calendar)
            print(f"{name} / month {month_idx}: {result}")
