from __future__ import annotations


def note_title(title: str | None, content: str) -> str:
    trimmed = (title or "").strip()
    if trimmed:
        return trimmed
    body = "".join((content or "").split())
    return body[:10]
