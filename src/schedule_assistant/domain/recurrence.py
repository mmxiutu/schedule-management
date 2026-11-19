from __future__ import annotations

import calendar
from datetime import date, datetime, time, timedelta

from schedule_assistant.domain.clock import TZ, parse_date

FREQ_DAILY = "daily"
FREQ_WEEKLY = "weekly"
FREQ_MONTHLY = "monthly"
FREQ_YEARLY = "yearly"


def clamp_month_day(year: int, month: int, day: int) -> date:
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last))


def occurrence_dates(rule: dict, window_start: date, window_end: date) -> list[date]:
    if not rule.get("enabled", True):
        return []
    freq = rule.get("freq") or FREQ_DAILY
    interval = int(rule.get("interval") or 1)
    if interval < 1:
        interval = 1
    start = parse_date(rule.get("startDate")) or window_start
    end = parse_date(rule.get("endDate"))
    cursor_end = window_end
    if end:
        cursor_end = min(cursor_end, end)
    if start > cursor_end:
        return []

    by_weekday = rule.get("byWeekday") or []
    by_month_day = rule.get("byMonthDay")
    month_day = int(by_month_day) if by_month_day else start.day

    dates: list[date] = []
    if freq == FREQ_DAILY:
        d = start
        if d < window_start:
            delta = (window_start - d).days
            skip = (delta // interval) * interval
            if skip < delta:
                skip += interval
            d = d + timedelta(days=skip)
        while d <= cursor_end:
            if d >= window_start:
                dates.append(d)
            d += timedelta(days=interval)
    elif freq == FREQ_WEEKLY:
        weekdays = set(int(x) for x in by_weekday) if by_weekday else {start.weekday()}
        d = window_start
        while d <= cursor_end:
            if d >= start and d.weekday() in weekdays:
                weeks = (d - start).days // 7
                if weeks % interval == 0:
                    dates.append(d)
            d += timedelta(days=1)
    elif freq == FREQ_MONTHLY:
        y, m = start.year, start.month
        while True:
            try:
                d = clamp_month_day(y, m, month_day)
            except ValueError:
                break
            if d > cursor_end:
                break
            if d >= window_start and d >= start:
                dates.append(d)
            m += interval
            y += (m - 1) // 12
            m = (m - 1) % 12 + 1
    elif freq == FREQ_YEARLY:
        y = start.year
        while True:
            d = clamp_month_day(y, start.month, month_day)
            if d > cursor_end:
                break
            if d >= window_start and d >= start:
                dates.append(d)
            y += interval
    return dates


def instance_due_at(day: date, time_of_day: str | None) -> datetime:
    hour, minute = 9, 0
    if time_of_day:
        parts = time_of_day.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
    return datetime.combine(day, time(hour, minute), tzinfo=TZ)


def instance_id(rule_id: str, day: date) -> str:
    return f"task:recurring:{rule_id}:{day.isoformat()}"
