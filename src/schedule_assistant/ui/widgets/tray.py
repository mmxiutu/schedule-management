from __future__ import annotations

import threading
from typing import Callable

from PIL import Image
from pystray import Icon, Menu, MenuItem

from schedule_assistant.db.repo import mark_notified
from schedule_assistant.domain.clock import now
from schedule_assistant.domain.time_filters import due_for_reminder
from schedule_assistant.resources import app_icon_path


def _icon_image() -> Image.Image:
    path = app_icon_path()
    if path is not None:
        try:
            return Image.open(path).convert("RGBA")
        except Exception:
            pass
    return Image.new("RGBA", (64, 64), "#F47B20")


class TrayController:
    def __init__(self, on_show: Callable[[], None], on_quit: Callable[[], None], workspace):
        self.workspace = workspace
        self._on_show = on_show
        self._on_quit = on_quit
        self.icon: Icon | None = None
        try:
            self.icon = Icon(
                "schedule-assistant",
                _icon_image(),
                "日程管理助手",
                Menu(
                    MenuItem("打开主窗口", lambda: self._on_show()),
                    MenuItem("退出", lambda: self._on_quit()),
                ),
            )
            threading.Thread(target=self.icon.run, daemon=True).start()
        except Exception:
            self.icon = None

    def available(self) -> bool:
        return self.icon is not None

    def notify(self, title: str, body: str) -> None:
        if self.icon:
            try:
                self.icon.notify(body, title)
                return
            except Exception:
                pass
        self._on_show()

    def stop(self) -> None:
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass

    def scan_due(self) -> None:
        try:
            tasks = self.workspace.all_tasks()
        except Exception:
            return
        due = due_for_reminder(tasks)
        if not due or not self.workspace.client:
            return
        for task in due:
            title = task.get("title") or "任务到期"
            self.notify("到期提醒", title)
            try:
                mark_notified(self.workspace.client, task, now())
            except Exception:
                pass
        self._on_show()
