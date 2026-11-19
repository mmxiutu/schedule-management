from __future__ import annotations

from schedule_assistant.app_paths import ConnectionConfig, load_connection, save_connection
from schedule_assistant.db.client import CouchError, ScheduleCouchClient
from schedule_assistant.db.models import SETTINGS_ID, TYPE_NOTE, TYPE_PROJECT, TYPE_RECURRING, TYPE_SETTINGS, TYPE_TASK
from schedule_assistant.db.repo import get_settings
from schedule_assistant.services.recurrence import instantiate_window


class Workspace:
    def __init__(self) -> None:
        self.connection = load_connection()
        self.client: ScheduleCouchClient | None = None
        self.last_error: str | None = None
        self.docs: list[dict] = []
        self.connect()

    def connect(self, cfg: ConnectionConfig | None = None) -> bool:
        if cfg is not None:
            self.connection = cfg
            save_connection(cfg)
        self.client = ScheduleCouchClient(self.connection)
        try:
            self.client.ping()
            self.client.ensure_database()
            get_settings(self.client)
            self.reload()
            created = instantiate_window(self.client, self.docs)
            if created:
                self.reload()
            self.last_error = None
            return True
        except (CouchError, OSError) as exc:
            self.last_error = str(exc)
            return False

    def reload(self) -> None:
        self.docs = self.require_client().all_docs()

    def by_type(self, doc_type: str) -> list[dict]:
        return [d for d in self.docs if d.get("type") == doc_type]

    def require_client(self) -> ScheduleCouchClient:
        if self.client is None:
            raise CouchError("尚未配置数据库连接")
        if self.last_error:
            raise CouchError(self.last_error)
        return self.client

    def ping_preview(self, cfg: ConnectionConfig) -> str:
        probe = ScheduleCouchClient(cfg, timeout=(5.0, 10.0))
        info = probe.ping()
        version = info.get("version") or "ok"
        return f"连接成功（CouchDB {version}）"

    def all_tasks(self) -> list[dict]:
        return self.by_type(TYPE_TASK)

    def all_notes(self) -> list[dict]:
        notes = self.by_type(TYPE_NOTE)
        notes.sort(key=lambda d: d.get("createdAt") or "", reverse=True)
        return notes

    def all_recurring(self) -> list[dict]:
        return self.by_type(TYPE_RECURRING)

    def settings_doc(self) -> dict:
        for doc in self.docs:
            if doc.get("_id") == SETTINGS_ID or doc.get("type") == TYPE_SETTINGS:
                return doc
        return get_settings(self.require_client())

    def projects_by_id(self) -> dict[str, dict]:
        return {p["_id"]: p for p in self.by_type(TYPE_PROJECT) if p.get("_id")}
