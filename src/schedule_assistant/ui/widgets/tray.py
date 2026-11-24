from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable

from PIL import Image
from pystray import Icon, Menu, MenuItem

from schedule_assistant.db.repo import mark_notified
from schedule_assistant.domain.clock import now
from schedule_assistant.domain.time_filters import due_for_reminder
from schedule_assistant.resources import app_icon_path, linux_tray_host_path


def _icon_image() -> Image.Image:
    path = app_icon_path()
    if path is not None:
        try:
            return Image.open(path).convert("RGBA")
        except Exception:
            pass
    return Image.new("RGBA", (64, 64), "#F47B20")


class _LinuxTray:
    def __init__(self, proc: subprocess.Popen[str], on_show: Callable[[], None], on_quit: Callable[[], None]):
        self.proc = proc
        self._on_show = on_show
        self._on_quit = on_quit
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        stdout = self.proc.stdout
        if stdout is None:
            return
        for line in stdout:
            msg = line.strip()
            if msg == "open":
                self._on_show()
            elif msg == "quit":
                self._on_quit()

    def notify(self, title: str, body: str) -> None:
        stdin = self.proc.stdin
        if stdin is None or self.proc.poll() is not None:
            raise RuntimeError("linux tray stopped")
        title = title.replace("\t", " ").replace("\n", " ")
        body = body.replace("\t", " ").replace("\n", " ")
        stdin.write(f"notify\t{title}\t{body}\n")
        stdin.flush()

    def stop(self) -> None:
        try:
            if self.proc.stdin and self.proc.poll() is None:
                self.proc.stdin.write("stop\n")
                self.proc.stdin.flush()
        except Exception:
            pass
        try:
            self.proc.terminate()
        except Exception:
            pass


def _start_linux_tray(on_show: Callable[[], None], on_quit: Callable[[], None]) -> _LinuxTray | None:
    host = linux_tray_host_path()
    icon = app_icon_path()
    python = Path("/usr/bin/python3")
    if host is None or icon is None or not python.is_file():
        return None
    try:
        proc = subprocess.Popen(
            [str(python), str(host), str(icon)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
    except OSError:
        return None
    if proc.stdout is None:
        proc.kill()
        return None
    ready: dict[str, str] = {"line": ""}

    def _wait_ready() -> None:
        ready["line"] = proc.stdout.readline() if proc.stdout is not None else ""

    waiter = threading.Thread(target=_wait_ready, daemon=True)
    waiter.start()
    waiter.join(3)
    if ready["line"].strip() != "ready" or proc.poll() is not None:
        proc.kill()
        return None
    return _LinuxTray(proc, on_show, on_quit)


class TrayController:
    def __init__(self, on_show: Callable[[], None], on_quit: Callable[[], None], workspace):
        self.workspace = workspace
        self._on_show = on_show
        self._on_quit = on_quit
        self.icon: Icon | None = None
        self._linux: _LinuxTray | None = None
        if sys.platform.startswith("linux"):
            self._linux = _start_linux_tray(self._on_show, self._on_quit)
            if self._linux is not None:
                return
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
        return self._linux is not None or self.icon is not None

    def notify(self, title: str, body: str) -> None:
        if self._linux is not None:
            try:
                self._linux.notify(title, body)
                return
            except Exception:
                pass
        if self.icon:
            try:
                self.icon.notify(body, title)
                return
            except Exception:
                pass
        self._on_show()

    def stop(self) -> None:
        if self._linux is not None:
            self._linux.stop()
            self._linux = None
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
