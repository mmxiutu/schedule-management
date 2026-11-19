from datetime import datetime

from schedule_assistant.db.models import STATUS_DONE, STATUS_IN_PROGRESS, STATUS_NOT_STARTED
from schedule_assistant.domain.clock import TZ
from schedule_assistant.domain.time_filters import (
    board_done,
    board_in_progress,
    board_not_started,
    due_today_tasks,
    overdue_tasks,
    today_needed_tasks,
    undated_open_tasks,
)

AT = datetime(2026, 11, 19, 12, 0, tzinfo=TZ)


def task(**kwargs):
    base = {"title": "t", "status": STATUS_NOT_STARTED}
    base.update(kwargs)
    return base


def test_undated_open():
    tasks = [
        task(dueAt=None, title="no due"),
        task(dueAt="2026-11-19T12:00:00+08:00", title="dated"),
        task(dueAt=None, status=STATUS_DONE, title="done"),
    ]
    names = [t["title"] for t in undated_open_tasks(tasks)]
    assert names == ["no due"]


def test_overdue_and_today():
    tasks = [
        task(dueAt="2026-11-18T09:00:00+08:00", title="late"),
        task(dueAt="2026-11-19T18:00:00+08:00", title="today"),
        task(dueAt="2026-11-20T09:00:00+08:00", title="future"),
    ]
    assert [t["title"] for t in overdue_tasks(tasks, AT)] == ["late"]
    assert [t["title"] for t in due_today_tasks(tasks, AT)] == ["today"]


def test_today_needed_uses_start_when_no_due():
    tasks = [task(dueAt=None, startAt="2026-11-19T08:00:00+08:00", title="start today")]
    assert [t["title"] for t in today_needed_tasks(tasks, AT)] == ["start today"]


def test_board_windows():
    tasks = [
        task(status=STATUS_NOT_STARTED, dueAt="2026-11-25T09:00:00+08:00", title="soon"),
        task(status=STATUS_NOT_STARTED, dueAt="2027-01-01T09:00:00+08:00", title="far"),
        task(status=STATUS_IN_PROGRESS, dueAt="2026-11-19T18:00:00+08:00", title="doing"),
        task(
            status=STATUS_DONE,
            dueAt="2026-11-18T09:00:00+08:00",
            completedAt="2026-11-18T10:00:00+08:00",
            title="finished",
        ),
        task(
            status=STATUS_DONE,
            completedAt="2026-10-01T10:00:00+08:00",
            title="old",
        ),
    ]
    assert [t["title"] for t in board_not_started(tasks, AT)] == ["soon"]
    assert [t["title"] for t in board_in_progress(tasks, {}, AT)] == ["doing"]
    assert [t["title"] for t in board_done(tasks, AT)] == ["finished"]


def test_board_in_progress_project_span():
    tasks = [
        task(
            status=STATUS_IN_PROGRESS,
            dueAt="2026-12-01T09:00:00+08:00",
            projectId="p1",
            title="proj",
        )
    ]
    projects = {"p1": {"startDate": "2026-11-01", "deliveryDate": "2026-11-30"}}
    assert [t["title"] for t in board_in_progress(tasks, projects, AT)] == ["proj"]
