from __future__ import annotations

import uuid
from datetime import datetime

from schedule_assistant.db.client import ScheduleCouchClient
from schedule_assistant.db.models import (
    SETTINGS_ID,
    TYPE_NOTE,
    TYPE_PROJECT,
    TYPE_RECURRING,
    TYPE_SETTINGS,
    TYPE_TASK,
)
from schedule_assistant.domain.clock import iso_date, iso_dt, now
from schedule_assistant.domain.notes import note_title


def list_by_type(client: ScheduleCouchClient, doc_type: str) -> list[dict]:
    return client.find({"type": doc_type})


def list_tasks(client: ScheduleCouchClient) -> list[dict]:
    return list_by_type(client, TYPE_TASK)


def list_notes(client: ScheduleCouchClient) -> list[dict]:
    docs = list_by_type(client, TYPE_NOTE)
    docs.sort(key=lambda d: d.get("createdAt") or "", reverse=True)
    return docs


def list_projects(client: ScheduleCouchClient) -> list[dict]:
    docs = list_by_type(client, TYPE_PROJECT)
    docs.sort(key=lambda d: d.get("name") or "")
    return docs


def list_recurring(client: ScheduleCouchClient) -> list[dict]:
    return list_by_type(client, TYPE_RECURRING)


def get_settings(client: ScheduleCouchClient) -> dict:
    doc = client.get(SETTINGS_ID)
    if doc:
        return doc
    doc = {
        "_id": SETTINGS_ID,
        "type": TYPE_SETTINGS,
        "noteCategories": [],
        "calendarLegend": {},
    }
    return client.save(doc)


def save_settings(client: ScheduleCouchClient, doc: dict) -> dict:
    doc["type"] = TYPE_SETTINGS
    doc["_id"] = SETTINGS_ID
    return client.save(doc)


def new_id(prefix: str) -> str:
    return f"{prefix}:{uuid.uuid4()}"


def save_task(client: ScheduleCouchClient, doc: dict) -> dict:
    doc["type"] = TYPE_TASK
    if not doc.get("_id"):
        doc["_id"] = new_id("task")
    return client.save(doc)


def save_note(client: ScheduleCouchClient, doc: dict) -> dict:
    content = doc.get("content") or ""
    if not str(content).strip():
        raise ValueError("记事内容不能为空")
    doc["type"] = TYPE_NOTE
    doc["title"] = note_title(doc.get("title"), content)
    doc["content"] = content
    doc["category"] = doc.get("category") or ""
    stamp = now()
    if not doc.get("createdAt"):
        doc["createdAt"] = iso_dt(stamp)
    if not doc.get("createdDate"):
        doc["createdDate"] = iso_date(stamp.date())
    if not doc.get("_id"):
        doc["_id"] = new_id("note")
    return client.save(doc)


def save_project(client: ScheduleCouchClient, doc: dict) -> dict:
    doc["type"] = TYPE_PROJECT
    if not doc.get("_id"):
        doc["_id"] = new_id("project")
    return client.save(doc)


def save_recurring(client: ScheduleCouchClient, doc: dict) -> dict:
    doc["type"] = TYPE_RECURRING
    if not doc.get("_id"):
        doc["_id"] = new_id("recurring")
    if "enabled" not in doc:
        doc["enabled"] = True
    return client.save(doc)


def mark_notified(client: ScheduleCouchClient, task: dict, when: datetime) -> dict:
    task["notifiedAt"] = iso_dt(when)
    return save_task(client, task)
