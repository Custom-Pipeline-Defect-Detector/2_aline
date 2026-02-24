from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Iterable


def week_start(value: date | datetime | None) -> date | None:
    """Return ISO week start (Monday) for a date-like value."""
    if value is None:
        return None
    day = value.date() if isinstance(value, datetime) else value
    return day - timedelta(days=day.weekday())


def build_ncr_weekly_counts(
    created_dates: Iterable[datetime | date | None],
    closed_dates: Iterable[date | datetime | None],
) -> list[dict[str, int | str]]:
    opened_weekly: dict[date, int] = defaultdict(int)
    closed_weekly: dict[date, int] = defaultdict(int)

    for created_at in created_dates:
        bucket = week_start(created_at)
        if bucket is not None:
            opened_weekly[bucket] += 1

    for closed_date in closed_dates:
        bucket = week_start(closed_date)
        if bucket is not None:
            closed_weekly[bucket] += 1

    week_keys = sorted(set(opened_weekly) | set(closed_weekly))
    return [
        {
            "week": week.isoformat(),
            "opened": opened_weekly.get(week, 0),
            "closed": closed_weekly.get(week, 0),
        }
        for week in week_keys
    ]
