from __future__ import annotations

from schedule_assistant.db.client import CouchError, ScheduleCouchClient


def ensure_indexes(client: ScheduleCouchClient) -> None:
    specs = [
        (["type"], "by_type"),
        (["type", "dueAt"], "by_type_due"),
        (["type", "status", "dueAt"], "by_type_status_due"),
        (["type", "createdDate"], "by_type_created"),
        (["type", "projectId"], "by_type_project"),
    ]
    for fields, name in specs:
        try:
            client.put_index(fields, name)
        except CouchError:
            # Index creation may fail on older/restricted servers; queries still work unindexed.
            pass
