from datetime import date, datetime

from app.services.dashboard import build_ncr_weekly_counts, week_start


def test_week_start_uses_monday_for_dates_and_datetimes():
    assert week_start(date(2025, 1, 1)) == date(2024, 12, 30)
    assert week_start(datetime(2025, 1, 5, 11, 30)) == date(2024, 12, 30)


def test_build_ncr_weekly_counts_combines_opened_and_closed():
    created = [
        datetime(2025, 1, 6, 8, 0),
        datetime(2025, 1, 7, 9, 0),
        datetime(2025, 1, 13, 10, 0),
    ]
    closed = [
        date(2025, 1, 8),
        date(2025, 1, 15),
        None,
    ]

    assert build_ncr_weekly_counts(created, closed) == [
        {"week": "2025-01-06", "opened": 2, "closed": 1},
        {"week": "2025-01-13", "opened": 1, "closed": 1},
    ]


def test_build_ncr_weekly_counts_empty_inputs_returns_empty_list():
    assert build_ncr_weekly_counts([], []) == []
