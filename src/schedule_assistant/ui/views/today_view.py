from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from schedule_assistant.db.models import KIND_LABELS, KIND_NORMAL
from schedule_assistant.domain.clock import now, parse_dt, weekday_cn
from schedule_assistant.domain.time_filters import due_today_tasks, overdue_tasks, today_needed_tasks
from schedule_assistant.ui.widgets.listbox import DataListbox
from schedule_assistant.workspace import Workspace


class TodayView(ttk.Frame):
    def __init__(self, master, workspace: Workspace, on_edit):
        super().__init__(master)
        self.workspace = workspace
        self.on_edit = on_edit
        self.header = ttk.Label(self, font=("Segoe UI", 14, "bold"))
        self.stats = ttk.Label(self)
        self.header.pack(anchor="w", pady=(0, 4))
        self.stats.pack(anchor="w", pady=(0, 8))
        ttk.Label(self, text="逾期未完成").pack(anchor="w")
        self.overdue = DataListbox(self, height=8)
        self.overdue.pack(fill=tk.BOTH, expand=True)
        ttk.Label(self, text="今天需要完成").pack(anchor="w", pady=(8, 0))
        self.today_list = DataListbox(self, height=8)
        self.today_list.pack(fill=tk.BOTH, expand=True)
        self.overdue.bind("<Double-Button-1>", lambda e: self._open(self.overdue))
        self.today_list.bind("<Double-Button-1>", lambda e: self._open(self.today_list))

    def _open(self, widget: DataListbox) -> None:
        task = widget.current()
        if task:
            self.on_edit(task)

    def refresh(self) -> None:
        at = now()
        self.header.config(text=f"{at.date().isoformat()}  {weekday_cn(at.date())}")
        try:
            tasks = self.workspace.all_tasks()
            projects = self.workspace.projects_by_id()
        except Exception as exc:
            self.stats.config(text=str(exc))
            self.overdue.set_items([])
            self.today_list.set_items([])
            return
        overdue = overdue_tasks(tasks, at)
        due_today = due_today_tasks(tasks, at)
        needed = today_needed_tasks(tasks, at)
        self.stats.config(text=f"今日到期 {len(due_today)}  ·  逾期未完成 {len(overdue)}")
        self._fill(self.overdue, overdue, projects)
        self._fill(self.today_list, needed, projects)

    def _fill(self, widget: DataListbox, tasks: list[dict], projects: dict) -> None:
        items = []
        for task in tasks:
            kind = KIND_LABELS.get(task.get("kind") or KIND_NORMAL, "普通任务")
            proj = projects.get(task.get("projectId") or "")
            if proj:
                kind = f"{kind} / {proj.get('name')}"
            due = parse_dt(task.get("dueAt"))
            due_s = due.strftime("%H:%M") if due else "无截止"
            notes = (task.get("notes") or "").replace("\n", " ")
            items.append((f"[{kind}] {task.get('title') or ''}  ·  {due_s}  ·  {notes}", task))
        widget.set_items(items)
