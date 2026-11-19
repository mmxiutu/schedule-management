from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from schedule_assistant.db.client import CouchError
from schedule_assistant.db.models import KIND_NORMAL, STATUS_DONE, STATUS_LABELS, TYPE_PROJECT
from schedule_assistant.db.repo import save_task
from schedule_assistant.domain.clock import iso_dt, now, parse_dt, parse_user_dt
from schedule_assistant.ui.dialogs.project_dialog import ProjectDialog
from schedule_assistant.ui.tkutil import bind_escape_close, center_on_parent
from schedule_assistant.workspace import Workspace


class TaskDialog:
    def __init__(self, master, workspace: Workspace, task: dict | None = None):
        self.workspace = workspace
        self.task = dict(task or {"kind": KIND_NORMAL, "status": "not_started"})
        self.result = False
        self._proj_ids = [""]
        self.win = tk.Toplevel(master)
        self.win.withdraw()
        self.win.title("任务")
        self.win.transient(master)
        self.win.resizable(False, False)
        bind_escape_close(self.win)
        center_on_parent(self.win, 480, 420, master)
        self.win.deiconify()
        self.win.grab_set()
        self.win.focus_force()

        form = ttk.Frame(self.win)
        form.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        ttk.Label(form, text="标题").grid(row=0, column=0, sticky="w")
        self.title = ttk.Entry(form)
        self.title.insert(0, self.task.get("title") or "")
        self.title.grid(row=0, column=1, sticky="ew", pady=3)

        ttk.Label(form, text="状态").grid(row=1, column=0, sticky="w")
        self.status = ttk.Combobox(form, state="readonly", values=list(STATUS_LABELS.values()))
        self.status.set(STATUS_LABELS.get(self.task.get("status") or "not_started", "未开始"))
        self.status.grid(row=1, column=1, sticky="ew", pady=3)

        due = parse_dt(self.task.get("dueAt"))
        self.has_due = tk.BooleanVar(value=bool(due))
        ttk.Checkbutton(form, text="设置截止日期", variable=self.has_due, command=self._toggle).grid(
            row=2, column=0, sticky="w"
        )
        self.due = ttk.Entry(form)
        self.due.insert(0, due.strftime("%Y-%m-%d %H:%M") if due else now().strftime("%Y-%m-%d %H:%M"))
        self.due.grid(row=2, column=1, sticky="ew")

        start = parse_dt(self.task.get("startAt"))
        self.has_start = tk.BooleanVar(value=bool(start))
        ttk.Checkbutton(form, text="设置开始时间", variable=self.has_start, command=self._toggle).grid(
            row=3, column=0, sticky="w"
        )
        self.start = ttk.Entry(form)
        self.start.insert(0, start.strftime("%Y-%m-%d %H:%M") if start else now().strftime("%Y-%m-%d %H:%M"))
        self.start.grid(row=3, column=1, sticky="ew")

        ttk.Label(form, text="关联项目").grid(row=4, column=0, sticky="w")
        proj_row = ttk.Frame(form)
        proj_row.grid(row=4, column=1, sticky="ew")
        self.project = ttk.Combobox(proj_row, state="readonly")
        self.project.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(proj_row, text="新建项目", command=self._new_project).pack(side=tk.LEFT, padx=4)
        self._reload_projects(self.task.get("projectId"))

        ttk.Label(form, text="备注").grid(row=5, column=0, sticky="nw")
        self.notes = tk.Text(form, height=8)
        self.notes.insert("1.0", self.task.get("notes") or "")
        self.notes.grid(row=5, column=1, sticky="nsew")
        form.columnconfigure(1, weight=1)
        form.rowconfigure(5, weight=1)
        self._toggle()

        btns = ttk.Frame(self.win)
        btns.pack(pady=8)
        ttk.Button(btns, text="确定", command=self._save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="取消", command=self.win.destroy).pack(side=tk.LEFT)

    def _toggle(self) -> None:
        self.due.config(state=tk.NORMAL if self.has_due.get() else tk.DISABLED)
        self.start.config(state=tk.NORMAL if self.has_start.get() else tk.DISABLED)

    def _reload_projects(self, selected: str | None) -> None:
        labels = ["（无）"]
        self._proj_ids = [""]
        for proj in self.workspace.by_type(TYPE_PROJECT):
            labels.append(proj.get("name") or proj["_id"])
            self._proj_ids.append(proj["_id"])
        self.project["values"] = labels
        idx = self._proj_ids.index(selected) if selected in self._proj_ids else 0
        self.project.current(idx)

    def _new_project(self) -> None:
        dlg = ProjectDialog(self.win, self.workspace)
        if dlg.show():
            self.workspace.reload()
            self._reload_projects(dlg.project.get("_id"))

    def show(self) -> bool:
        self.win.wait_window()
        return self.result

    def _save(self) -> None:
        title = self.title.get().strip()
        if not title:
            messagebox.showwarning("校验", "请填写任务标题", parent=self.win)
            return
        status_label = self.status.get()
        status = next((k for k, v in STATUS_LABELS.items() if v == status_label), "not_started")
        due_at = iso_dt(parse_user_dt(self.due.get())) if self.has_due.get() else None
        start_at = iso_dt(parse_user_dt(self.start.get())) if self.has_start.get() else None
        pidx = max(0, self.project.current())
        self.task.update(
            {
                "title": title,
                "notes": self.notes.get("1.0", tk.END).strip(),
                "status": status,
                "dueAt": due_at,
                "startAt": start_at,
                "projectId": self._proj_ids[pidx] if pidx < len(self._proj_ids) else "",
                "kind": self.task.get("kind") or KIND_NORMAL,
            }
        )
        if status == STATUS_DONE and not self.task.get("completedAt"):
            self.task["completedAt"] = iso_dt(now())
        if status != STATUS_DONE:
            self.task["completedAt"] = None
        try:
            self.task = save_task(self.workspace.require_client(), self.task)
        except CouchError as exc:
            messagebox.showwarning("保存失败", str(exc), parent=self.win)
            return
        self.result = True
        self.win.destroy()
