from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from schedule_assistant.db.models import STATUS_LABELS, STATUS_NOT_STARTED
from schedule_assistant.db.repo import save_project
from schedule_assistant.domain.clock import iso_date, parse_user_date, today
from schedule_assistant.workspace import Workspace


class ProjectDialog:
    def __init__(self, master, workspace: Workspace, project: dict | None = None):
        self.workspace = workspace
        self.project = dict(project or {})
        self.result = False
        self.win = tk.Toplevel(master)
        self.win.title("轻量项目")
        self.win.geometry("420x380")
        self.win.transient(master)
        self.win.grab_set()

        form = ttk.Frame(self.win)
        form.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        self.name = self._entry(form, 0, "名称", self.project.get("name") or "")
        ttk.Label(form, text="描述").grid(row=1, column=0, sticky="nw")
        self.description = tk.Text(form, height=4)
        self.description.insert("1.0", self.project.get("description") or "")
        self.description.grid(row=1, column=1, sticky="ew")
        self.start = self._entry(form, 2, "立项时间", self.project.get("startDate") or today().isoformat())
        self.delivery = self._entry(form, 3, "交付时间", self.project.get("deliveryDate") or today().isoformat())
        self.payment = self._entry(form, 4, "收款时间", self.project.get("paymentDate") or today().isoformat())
        self.amount = self._entry(form, 5, "金额", str(self.project.get("amount") or "0"))
        ttk.Label(form, text="状态").grid(row=6, column=0, sticky="w")
        self.status = ttk.Combobox(form, state="readonly", values=list(STATUS_LABELS.values()))
        current = STATUS_LABELS.get(self.project.get("status") or STATUS_NOT_STARTED)
        self.status.set(current or "未开始")
        self.status.grid(row=6, column=1, sticky="ew")
        form.columnconfigure(1, weight=1)

        btns = ttk.Frame(self.win)
        btns.pack(pady=8)
        ttk.Button(btns, text="确定", command=self._save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="取消", command=self.win.destroy).pack(side=tk.LEFT)

    def _entry(self, form, row, label, value) -> ttk.Entry:
        ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=3)
        entry = ttk.Entry(form)
        entry.insert(0, value)
        entry.grid(row=row, column=1, sticky="ew", pady=3)
        return entry

    def show(self) -> bool:
        self.win.wait_window()
        return self.result

    def _save(self) -> None:
        name = self.name.get().strip()
        if not name:
            self.name.focus_set()
            return
        status_label = self.status.get()
        status_key = next((k for k, v in STATUS_LABELS.items() if v == status_label), STATUS_NOT_STARTED)
        try:
            amount = float(self.amount.get() or 0)
        except ValueError:
            amount = 0
        self.project.update(
            {
                "name": name,
                "description": self.description.get("1.0", tk.END).strip(),
                "startDate": iso_date(parse_user_date(self.start.get()) or today()),
                "deliveryDate": iso_date(parse_user_date(self.delivery.get()) or today()),
                "paymentDate": iso_date(parse_user_date(self.payment.get()) or today()),
                "amount": amount,
                "status": status_key,
            }
        )
        self.project = save_project(self.workspace.require_client(), self.project)
        self.result = True
        self.win.destroy()
