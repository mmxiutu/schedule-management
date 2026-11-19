from __future__ import annotations

from typing import Any

import requests

from schedule_assistant.app_paths import ConnectionConfig


class CouchError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class ScheduleCouchClient:
    def __init__(self, cfg: ConnectionConfig, timeout: float | tuple[float, float] = (8.0, 20.0)):
        self.cfg = cfg
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = (cfg.user, cfg.password)
        self.session.headers["Accept"] = "application/json"
        self.base = cfg.url.rstrip("/")
        self.db = cfg.db.strip("/") or "schedule_assistant"

    def _url(self, *parts: str) -> str:
        extra = "/".join(p.strip("/") for p in parts if p)
        if extra:
            return f"{self.base}/{extra}"
        return self.base

    def _raise(self, resp: requests.Response, default: str) -> None:
        try:
            payload = resp.json()
            reason = payload.get("reason") or payload.get("error") or resp.text
        except Exception:
            reason = resp.text or default
        raise CouchError(f"{default}: {reason}", status=resp.status_code)

    def ping(self) -> dict[str, Any]:
        resp = self.session.get(self.base, timeout=self.timeout)
        if not resp.ok:
            self._raise(resp, "连接失败")
        return resp.json()

    def ensure_database(self) -> None:
        resp = self.session.put(self._url(self.db), timeout=self.timeout)
        if resp.status_code in (201, 202, 412):
            return
        if not resp.ok:
            self._raise(resp, "无法创建或访问数据库")

    def get(self, doc_id: str) -> dict[str, Any] | None:
        resp = self.session.get(self._url(self.db, doc_id), timeout=self.timeout)
        if resp.status_code == 404:
            return None
        if not resp.ok:
            self._raise(resp, "读取文档失败")
        return resp.json()

    def save(self, doc: dict[str, Any]) -> dict[str, Any]:
        doc_id = doc.get("_id")
        if doc_id:
            resp = self.session.put(self._url(self.db, doc_id), json=doc, timeout=self.timeout)
        else:
            resp = self.session.post(self._url(self.db), json=doc, timeout=self.timeout)
        if resp.status_code == 409:
            self._raise(resp, "文档冲突，请刷新后重试")
        if not resp.ok:
            self._raise(resp, "保存失败")
        body = resp.json()
        doc["_id"] = body.get("id", doc_id)
        doc["_rev"] = body.get("rev")
        return doc

    def delete(self, doc: dict[str, Any]) -> None:
        doc_id = doc.get("_id")
        rev = doc.get("_rev")
        if not doc_id or not rev:
            raise CouchError("删除需要 _id 与 _rev")
        resp = self.session.delete(
            self._url(self.db, doc_id),
            params={"rev": rev},
            timeout=self.timeout,
        )
        if not resp.ok:
            self._raise(resp, "删除失败")

    def find(self, selector: dict[str, Any], limit: int = 1000, sort: list | None = None) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"selector": selector, "limit": limit}
        if sort:
            payload["sort"] = sort
        resp = self.session.post(self._url(self.db, "_find"), json=payload, timeout=self.timeout)
        if not resp.ok:
            self._raise(resp, "查询失败")
        return list(resp.json().get("docs") or [])

    def all_docs(self) -> list[dict[str, Any]]:
        resp = self.session.get(
            self._url(self.db, "_all_docs"),
            params={"include_docs": "true"},
            timeout=self.timeout,
        )
        if not resp.ok:
            self._raise(resp, "读取全部文档失败")
        docs: list[dict[str, Any]] = []
        for row in resp.json().get("rows") or []:
            doc = row.get("doc")
            if not doc or str(doc.get("_id", "")).startswith("_design/"):
                continue
            docs.append(doc)
        return docs

    def bulk_save(self, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not docs:
            return []
        resp = self.session.post(
            self._url(self.db, "_bulk_docs"),
            json={"docs": docs},
            timeout=self.timeout,
        )
        if not resp.ok:
            self._raise(resp, "批量保存失败")
        results = resp.json()
        by_id = {item.get("id"): item for item in results if isinstance(item, dict)}
        for doc in docs:
            info = by_id.get(doc.get("_id"))
            if info and info.get("rev"):
                doc["_rev"] = info["rev"]
        return docs

    def put_index(self, fields: list[str], name: str) -> None:
        payload = {"index": {"fields": fields}, "name": name, "type": "json"}
        resp = self.session.post(self._url(self.db, "_index"), json=payload, timeout=self.timeout)
        if not resp.ok:
            self._raise(resp, f"创建索引失败 ({name})")
