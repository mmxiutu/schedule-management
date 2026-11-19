from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

APP_DIR_NAME_WIN = "ScheduleAssistant"
APP_DIR_NAME_UNIX = "schedule-assistant"


@dataclass
class ConnectionConfig:
    url: str = ""
    user: str = ""
    password: str = ""
    db: str = ""

    def normalized_url(self) -> str:
        return self.url.rstrip("/") + "/" if self.url else ""


def config_dir() -> Path:
    if sys.platform.startswith("win"):
        root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(root) / APP_DIR_NAME_WIN
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / APP_DIR_NAME_UNIX
    return Path.home() / ".config" / APP_DIR_NAME_UNIX


def connection_path() -> Path:
    return config_dir() / "connection.json"


def load_connection() -> ConnectionConfig:
    path = connection_path()
    if not path.exists():
        return ConnectionConfig()
    data = json.loads(path.read_text(encoding="utf-8"))
    return ConnectionConfig(
        url=(data.get("url") or "").strip(),
        user=(data.get("user") or "").strip(),
        password=data.get("password") or "",
        db=(data.get("db") or "").strip(),
    )


def save_connection(cfg: ConnectionConfig) -> None:
    path = connection_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(cfg), ensure_ascii=False, indent=2), encoding="utf-8")
