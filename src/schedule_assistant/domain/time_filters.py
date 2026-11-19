from __future__ import annotations

from datetime import date, datetime, timedelta

from schedule_assistant.domain.clock import TZ, day_start, parse_date, parse_dt, today
from schedule_assistant.db.models import STATUS_DONE, STATUS_IN_PROGRESS, STATUS_NOT_STARTED


def _task_due(task: dict) -> datetime | None:
    return parse_dt(task.get("dueAt"))


def _task_start(task: dict) -> datetime | None:
    return parse_dt(task.get("startAt"))


def is_incomplete(task: dict) -> bool:
    return task.get("status") != STATUS_DONE


def undated_open_tasks(tasks: list[dict]) -> list[dict]:
    result = []
    for task in tasks:
        if not is_incomplete(task):
            continue
        if _task_due(task) is None:
            result.append(task)
    return result


def overdue_tasks(tasks: list[dict], at: datetime | None = None) -> list[dict]:
    at = at or datetime.now(TZ)
    start = day_start(at.date())
    result = []
    for task in tasks:
        if not is_incomplete(task):
            continue
        due = _task_due(task)
        if due is not None and due < start:
            result.append(task)
    return result


def due_today_tasks(tasks: list[dict], at: datetime | None = None) -> list[dict]:
    at = at or datetime.now(TZ)
    start = day_start(at.date())
    end = start + timedelta(days=1)
    result = []
    for task in tasks:
        if not is_incomplete(task):
            continue
        due = _task_due(task)
        if due is not None and start <= due < end:
            result.append(task)
    return result


def today_needed_tasks(tasks: list[dict], at: datetime | None = None) -> list[dict]:
    at = at or datetime.now(TZ)
    start = day_start(at.date())
    end = start + timedelta(days=1)
    result = []
    for task in tasks:
        if not is_incomplete(task):
            continue
        due = _task_due(task)
        begin = _task_start(task)
        if due is not None and start <= due < end:
            result.append(task)
        elif due is None and begin is not None and start <= begin < end:
            result.append(task)
    return result


def _in_window(point: datetime, lo: datetime, hi: datetime) -> bool:
    return lo <= point <= hi


def task_anchor_time(task: dict) -> datetime | None:
    due = _task_due(task)
    if due is not None:
        return due
    return _task_start(task)


def task_span_contains_day(task: dict, day: date) -> bool:
    start = _task_start(task)
    due = _task_due(task)
    day_lo = day_start(day)
    day_hi = day_lo + timedelta(days=1) - timedelta(microseconds=1)
    if start and due:
        return start <= day_hi and due >= day_lo
    if due:
        return day_lo <= due < day_lo + timedelta(days=1)
    if start:
        return day_lo <= start < day_lo + timedelta(days=1)
    return False


def project_spans_day(project: dict | None, day: date) -> bool:
    if not project:
        return False
    start = parse_date(project.get("startDate"))
    end = parse_date(project.get("deliveryDate"))
    if start and end:
        return start <= day <= end
    if start:
        return start == day
    if end:
        return end == day
    return False


def board_not_started(tasks: list[dict], at: datetime | None = None) -> list[dict]:
    at = at or datetime.now(TZ)
    hi = at + timedelta(days=30)
    result = []
    for task in tasks:
        if task.get("status") != STATUS_NOT_STARTED:
            continue
        due = _task_due(task)
        start = _task_start(task)
        if due is not None:
            if _in_window(due, at, hi):
                result.append(task)
            continue
        if start is not None and _in_window(start, at, hi):
            result.append(task)
    return result


def board_in_progress(
    tasks: list[dict],
    projects_by_id: dict[str, dict] | None = None,
    at: datetime | None = None,
) -> list[dict]:
    at = at or datetime.now(TZ)
    day = at.date()
    projects_by_id = projects_by_id or {}
    start = day_start(day)
    end = start + timedelta(days=1)
    result = []
    for task in tasks:
        if task.get("status") != STATUS_IN_PROGRESS:
            continue
        due = _task_due(task)
        due_today = due is not None and start <= due < end
        project = projects_by_id.get(task.get("projectId") or "")
        if due_today or project_spans_day(project, day) or task_span_contains_day(task, day):
            result.append(task)
    return result


def board_done(tasks: list[dict], at: datetime | None = None) -> list[dict]:
    at = at or datetime.now(TZ)
    day = at.date()
    lo = day_start(day - timedelta(days=7))
    hi = day_start(day) + timedelta(days=1)
    result = []
    for task in tasks:
        if task.get("status") != STATUS_DONE:
            continue
        stamp = parse_dt(task.get("completedAt")) or _task_due(task)
        if stamp is None:
            continue
        if lo <= stamp < hi:
            result.append(task)
    return result


def due_for_reminder(tasks: list[dict], at: datetime | None = None) -> list[dict]:
    at = at or datetime.now(TZ)
    result = []
    for task in tasks:
        if not is_incomplete(task):
            continue
        if task.get("notifiedAt"):
            continue
        due = _task_due(task)
        if due is not None and due <= at:
            result.append(task)
    return result


def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def three_week_days(page_monday: date) -> list[date]:
    return [page_monday + timedelta(days=i) for i in range(21)]
