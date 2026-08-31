"""Synthetic year-long activity grid.

Deterministic by construction: the same seed and the same window produce the
same picture, so a rebuild that changes nothing leaves the PNG byte-identical
and the scheduled workflow does not churn commits.

Baseline noise is generated for the whole 53-week window before future days are
blanked out, so the pattern for days already drawn never shifts as time passes —
the grid only grows to the right.
"""

from datetime import date, timedelta

WEEKS = 53
DAYS = WEEKS * 7

SEED = 0x5EED_1337

FLARES = 20            # short bursts
FLARE_LEN = (3, 7)
FLARE_PEAK = (8, 34)

SPRINTS = 3            # long stretches of dense work
SPRINT_LEN = (10, 20)
SPRINT_ADD = (5, 12)

# Level thresholds. Level 0 is reserved for days that have not happened yet;
# every past day lands on level 1 or higher because the baseline starts at 1.
THRESHOLDS = ((2, 1), (6, 2), (14, 3))


def mulberry32(seed):
    """Small, fast, fully specified PRNG — identical output on every machine."""
    state = seed & 0xFFFFFFFF

    def rnd():
        nonlocal state
        state = (state + 0x6D2B79F5) & 0xFFFFFFFF
        t = state
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t = (t ^ (t + ((t ^ (t >> 7)) * (t | 61) & 0xFFFFFFFF))) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0

    return rnd


def level_of(count):
    if count <= 0:
        return 0
    for ceiling, lvl in THRESHOLDS:
        if count <= ceiling:
            return lvl
    return 4


def build(today=None, seed=SEED):
    """Return (days, start, end) where days is a flat list of DAYS entries.

    Column c, row r of the drawn grid is days[c * 7 + r]; row 0 is Sunday, so
    the layout matches the calendar people expect to see.
    """
    today = today or date.today()
    # The rightmost column always ends on a Saturday, as on a real calendar.
    end = today + timedelta(days=(5 - today.weekday()) % 7)
    start = end - timedelta(days=DAYS - 1)

    rnd = mulberry32(seed ^ (start.toordinal() & 0xFFFFFFFF))
    counts = [0] * DAYS

    # Daily baseline: never zero, lighter on weekends.
    for i in range(DAYS):
        weekend = (start + timedelta(days=i)).weekday() >= 5
        counts[i] = 1 + int(rnd() * (2 if weekend else 3))

    # Short bursts with a triangular falloff from the centre of the window.
    lo, hi = FLARE_LEN
    plo, phi = FLARE_PEAK
    for _ in range(FLARES):
        centre = int(rnd() * DAYS)
        length = lo + int(rnd() * (hi - lo + 1))
        peak = plo + int(rnd() * (phi - plo + 1))
        half = length / 2.0
        for j in range(centre - length // 2, centre + length - length // 2):
            if 0 <= j < DAYS:
                falloff = 1.0 - abs(j - centre) / (half + 0.5)
                counts[j] += max(0, int(peak * falloff))

    # Longer stretches, so the year reads as periods of work and not only spikes.
    slo, shi = SPRINT_LEN
    alo, ahi = SPRINT_ADD
    for _ in range(SPRINTS):
        head = int(rnd() * DAYS)
        length = slo + int(rnd() * (shi - slo + 1))
        add = alo + int(rnd() * (ahi - alo + 1))
        for j in range(head, head + length):
            if 0 <= j < DAYS:
                counts[j] += add + int(rnd() * 3)

    # Days that have not happened yet stay blank, the way a real calendar looks.
    days = []
    for i in range(DAYS):
        d = start + timedelta(days=i)
        count = 0 if d > today else counts[i]
        days.append({'date': d, 'count': count, 'level': level_of(count)})

    return days, start, end


def stats(days, today=None):
    today = today or date.today()
    past = [d for d in days if d['date'] <= today]
    dist = {lvl: sum(1 for d in past if d['level'] == lvl) for lvl in range(5)}
    return {
        'past_days': len(past),
        'future_days': len(days) - len(past),
        'total': sum(d['count'] for d in past),
        'min_per_day': min(d['count'] for d in past),
        'max_per_day': max(d['count'] for d in past),
        'levels': dist,
    }
