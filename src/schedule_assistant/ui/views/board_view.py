from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from schedule_assistant.db.client import CouchError
from schedule_assistant.db.models import STATUS_DONE, STATUS_IN_PROGRESS, STATUS_NOT_STARTED
from schedule_assistant.db.repo import save_task
from schedule_assistant.domain.clock import iso_dt, now, parse_dt
from schedule_assistant.domain.time_filters import board_done, board_in_progress, board_not_started
from schedule_assistant.ui.widgets.listbox import DataListbox
from schedule_assistant.workspace import Workspace

COLUMNS = [
    ("未开始", STATUS_NOT_STARTED),
    ("进行中", STATUS_IN_PROGRESS),
    ("已完成", STATUS_DONE),
]


class BoardView(ttk.Frame):
    def __init__(self, master, workspace: Workspace, on_edit):
        super().__init__(master)
        self.workspace = workspace
        self.on_edit = on_edit
        self.lists: dict[str, DataListbox] = {}
        for col, (title, status) in enumerate(COLUMNS):
            box = ttk.Frame(self)
            box.grid(row=0, column=col, sticky="nsew", padx=4)
            self.columnconfigure(col, weight=1)
            ttk.Label(box, text=title).pack(anchor="w")
            lst = DataListbox(box)
            lst.pack(fill=tk.BOTH, expand=True)
            lst.bind("<Double-Button-1>", lambda e, w=lst: self._edit(w))
            lst.bind("<Button-3>", lambda e, s=status, w=lst: self._menu(e, s, w))
            self.lists[status] = lst
        self.rowconfigure(0, weight=1)

    def _edit(self, widget: DataListbox) -> None:
        task = widget.current()
        if task:
            self.on_edit(task)

    def _menu(self, event, status: str, widget: DataListbox) -> None:
        widget.selection_clear(0, tk.END)
        widget.selection_set(widget.nearest(event.y))
        task = widget.current()
        if not task:
            return
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="编辑", command=lambda: self.on_edit(task))
        for title, st in COLUMNS:
            if st != status:
                menu.add_command(label=f"移到{title}", command=lambda s=st, t=task: self._move(t, s))
        menu.tk_popup(event.x_root, event.y_root)

    def _move(self, task: dict, status: str) -> None:
        try:
            client = self.workspace.require_client()
            task["status"] = status
            task["completedAt"] = iso_dt(now()) if status == STATUS_DONE else None
            save_task(client, task)
            self.workspace.reload()
        except CouchError as exc:
            messagebox.showwarning("无法保存", str(exc), parent=self)
        self.refresh()

    def refresh(self) -> None:
        try:
            tasks = self.workspace.all_tasks()
            projects = self.workspace.projects_by_id()
        except Exception as exc:
            for lst in self.lists.values():
                lst.set_items([(str(exc), None)])
            return
        grouped = {
            STATUS_NOT_STARTED: board_not_started(tasks),
            STATUS_IN_PROGRESS: board_in_progress(tasks, projects),
            STATUS_DONE: board_done(tasks),
        }
        for status, lst in self.lists.items():
            items = []
            for task in grouped[status]:
                due = parse_dt(task.get("dueAt"))
                due_s = due.strftime("%m-%d %H:%M") if due else "无截止"
                items.append((f"{task.get('title') or ''}  {due_s}", task))
            lst.set_items(items)
