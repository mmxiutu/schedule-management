from __future__ import annotations

from datetime import timedelta

from schedule_assistant.db.client import ScheduleCouchClient
from schedule_assistant.db.models import KIND_RECURRING, STATUS_NOT_STARTED, TYPE_RECURRING, TYPE_TASK
from schedule_assistant.domain.clock import iso_dt, today
from schedule_assistant.domain.recurrence import instance_due_at, instance_id, occurrence_dates


def instantiate_window(
    client: ScheduleCouchClient,
    docs: list[dict] | None = None,
    days: int = 60,
) -> int:
    """Only create missing instances. Existing docs are left untouched (no per-day GET/PUT)."""
    if docs is None:
        docs = client.all_docs()
    by_id = {d["_id"]: d for d in docs if d.get("_id")}
    start = today()
    end = start + timedelta(days=days)
    to_create: list[dict] = []
    for rule in docs:
        if rule.get("type") != TYPE_RECURRING:
            continue
        rule_id = rule.get("_id")
        if not rule_id:
            continue
        for day in occurrence_dates(rule, start, end):
            doc_id = instance_id(rule_id, day)
            existing = by_id.get(doc_id)
            if existing:
                continue
            to_create.append(
                {
                    "_id": doc_id,
                    "type": TYPE_TASK,
                    "kind": KIND_RECURRING,
                    "title": rule.get("title") or "周期任务",
                    "notes": rule.get("notes") or "",
                    "status": STATUS_NOT_STARTED,
                    "dueAt": iso_dt(instance_due_at(day, rule.get("timeOfDay"))),
                    "startAt": None,
                    "projectId": rule.get("projectId") or "",
                    "recurringRuleId": rule_id,
                    "instanceDate": day.isoformat(),
                }
            )
    if to_create:
        client.bulk_save(to_create)
    return len(to_create)
