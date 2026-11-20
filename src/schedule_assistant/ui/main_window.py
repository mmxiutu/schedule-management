from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from schedule_assistant.ui.dialogs.recurring_dialog import RecurringDialog
from schedule_assistant.ui.dialogs.settings_dialog import SettingsDialog
from schedule_assistant.ui.dialogs.task_dialog import TaskDialog
from datetime import date, datetime, time

from schedule_assistant.db.models import KIND_NORMAL
from schedule_assistant.domain.clock import TZ, iso_dt
from schedule_assistant.resources import app_icon_path
from schedule_assistant.ui.theme import COLOR_BANNER, COLOR_BG
from schedule_assistant.ui.views.board_view import BoardView
from schedule_assistant.ui.views.month_view import MonthView
from schedule_assistant.ui.views.notes_view import NotesView
from schedule_assistant.ui.views.standby_view import StandbyView
from schedule_assistant.ui.views.today_view import TodayView
from schedule_assistant.ui.widgets.tray import TrayController
from schedule_assistant.workspace import Workspace

NAV = ["月历", "今日", "看板", "记事本"]


class MainWindow:
    def __init__(self, root: tk.Tk, workspace: Workspace):
        self.root = root
        self.workspace = workspace
        self._force_quit = False
        self._standby_on = False
        self.root.title("日程管理助手")
        self.root.geometry("1280x720")
        self.root.minsize(1100, 680)
        self.root.configure(bg=COLOR_BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._apply_window_icon()

        self.banner = tk.Label(root, text="", bg=COLOR_BANNER, fg="#000", anchor="w")
        top = ttk.Frame(root)
        self._top = top
        top.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(top, text="新建任务", command=lambda: self._open_task()).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="周期任务", command=self._open_recurring).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="设置", command=self._open_settings).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="待机", command=self._enter_standby).pack(side=tk.LEFT, padx=3)

        body = ttk.Frame(root)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        nav_frame = tk.Frame(body, bg=COLOR_BG)
        nav_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(4, 16), pady=12)
        self.nav_buttons: list[tk.Button] = []
        self._nav_index = 0
        for i, name in enumerate(NAV):
            btn = tk.Button(
                nav_frame,
                text=name,
                width=10,
                height=2,
                bd=2,
                cursor="hand2",
                font=("Microsoft YaHei UI", 11),
                command=lambda idx=i: self._goto(idx),
            )
            btn.pack(fill=tk.X, pady=(0, 22))
            self.nav_buttons.append(btn)

        self.stack = ttk.Frame(body)
        self.stack.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.month = MonthView(self.stack, workspace, self._open_task, self._open_task_for_day)
        self.today = TodayView(self.stack, workspace, self._open_task)
        self.board = BoardView(self.stack, workspace, self._open_task)
        self.notes = NotesView(self.stack, workspace)
        self.views = (self.month, self.today, self.board, self.notes)
        for view in self.views:
            view.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._goto(0)

        self.standby = StandbyView(self.root, self._leave_standby)
        self.tray = TrayController(self.show_normal, self.force_quit, workspace)
        self._schedule_remind()
        if workspace.last_error:
            self.show_banner(f"数据库未连通：{workspace.last_error}。请打开「设置」测试连接。")
        else:
            self.root.after(50, self.refresh_all)

    def _apply_window_icon(self) -> None:
        path = app_icon_path()
        if path is None:
            return
        try:
            icon = tk.PhotoImage(file=str(path), master=self.root)
            self.root.iconphoto(True, icon)
            self.root._app_icon = icon  # keep PhotoImage alive
        except Exception:
            pass

    def show_banner(self, text: str) -> None:
        self.banner.config(text=text)
        if not self.banner.winfo_ismapped():
            self.banner.pack(fill=tk.X, before=self._top)
        self.root.after(8000, lambda: self.banner.pack_forget())

    def show_normal(self) -> None:
        self.root.after(0, self._show_today_ui)

    def _show_today_ui(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self._goto(1)

    def show_today(self) -> None:
        self.show_normal()

    def refresh_all(self) -> None:
        try:
            if not self.workspace.last_error:
                self.workspace.reload()
        except Exception as exc:
            self.show_banner(str(exc))
        for view in self.views:
            view.refresh()

    def _goto(self, row: int) -> None:
        self._nav_index = row
        for i, btn in enumerate(self.nav_buttons):
            if i == row:
                btn.config(
                    relief=tk.SUNKEN,
                    bg="#B3E5FC",
                    fg="#0D47A1",
                    activebackground="#81D4FA",
                    font=("Microsoft YaHei UI", 11, "bold"),
                )
            else:
                btn.config(
                    relief=tk.RAISED,
                    bg="#FFFFFF",
                    fg="#222222",
                    activebackground="#EEEEEE",
                    font=("Microsoft YaHei UI", 11),
                )
        self.views[row].lift()
        self.views[row].refresh()

    def _open_task(self, task: dict | None = None) -> None:
        if self.workspace.last_error or self.workspace.client is None:
            messagebox.showwarning("未连接", "请先在设置中连接 CouchDB", parent=self.root)
            return
        if TaskDialog(self.root, self.workspace, task).show():
            self.refresh_all()

    def _open_task_for_day(self, day: date) -> None:
        due = datetime.combine(day, time(18, 0), tzinfo=TZ)
        self._open_task(
            {
                "kind": KIND_NORMAL,
                "status": "not_started",
                "dueAt": iso_dt(due),
            }
        )

    def _open_recurring(self) -> None:
        if self.workspace.last_error or self.workspace.client is None:
            messagebox.showwarning("未连接", "请先在设置中连接 CouchDB", parent=self.root)
            return
        RecurringDialog(self.root, self.workspace).show()
        self.refresh_all()

    def _open_settings(self) -> None:
        if SettingsDialog(self.root, self.workspace).show():
            self.banner.pack_forget()
            self.refresh_all()

    def force_quit(self) -> None:
        self._force_quit = True
        self.root.after(0, self._do_quit)

    def _do_quit(self) -> None:
        self._leave_standby()
        self.tray.stop()
        self.root.destroy()

    def _enter_standby(self) -> None:
        if self._standby_on:
            self._leave_standby()
            return
        self._standby_on = True
        self.standby.start()

    def _leave_standby(self) -> None:
        self._standby_on = False
        self.standby.stop()

    def _on_close(self) -> None:
        if self.tray.available() and not self._force_quit:
            self.root.withdraw()
            return
        self.force_quit()

    def _schedule_remind(self) -> None:
        self.tray.scan_due()
        self.root.after(60_000, self._schedule_remind)
