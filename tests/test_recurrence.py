from datetime import date

from schedule_assistant.domain.recurrence import clamp_month_day, occurrence_dates


def test_month_day_31_clamps_to_february():
    assert clamp_month_day(2026, 2, 31) == date(2026, 2, 28)


def test_daily_interval():
    rule = {"freq": "daily", "interval": 2, "startDate": "2026-11-19", "enabled": True}
    days = occurrence_dates(rule, date(2026, 11, 19), date(2026, 11, 25))
    assert days == [
        date(2026, 11, 19),
        date(2026, 11, 21),
        date(2026, 11, 23),
        date(2026, 11, 25),
    ]


def test_weekly_weekdays():
    rule = {
        "freq": "weekly",
        "interval": 1,
        "startDate": "2026-11-16",
        "byWeekday": [0, 2],
        "enabled": True,
    }
    days = occurrence_dates(rule, date(2026, 11, 16), date(2026, 11, 22))
    assert days == [date(2026, 11, 16), date(2026, 11, 18)]


def test_monthly_31_in_short_month():
    rule = {
        "freq": "monthly",
        "interval": 1,
        "startDate": "2026-01-31",
        "byMonthDay": 31,
        "enabled": True,
    }
    days = occurrence_dates(rule, date(2026, 1, 1), date(2026, 3, 31))
    assert date(2026, 2, 28) in days
    assert date(2026, 1, 31) in days
    assert date(2026, 3, 31) in days
