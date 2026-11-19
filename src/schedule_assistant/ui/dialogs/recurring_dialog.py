from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from schedule_assistant.db.client import CouchError
from schedule_assistant.db.models import TYPE_PROJECT
from schedule_assistant.db.repo import save_recurring
from schedule_assistant.domain.clock import iso_date, parse_user_date, today
from schedule_assistant.domain.recurrence import FREQ_DAILY, FREQ_MONTHLY, FREQ_WEEKLY, FREQ_YEARLY
from schedule_assistant.services.recurrence import instantiate_window
from schedule_assistant.ui.widgets.listbox import DataListbox
from schedule_assistant.workspace import Workspace

FREQ_LABELS = {
    FREQ_DAILY: "每天",
    FREQ_WEEKLY: "每周",
    FREQ_MONTHLY: "每月",
    FREQ_YEARLY: "每年",
}
WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


class RecurringDialog:
    def __init__(self, master, workspace: Workspace):
        self.workspace = workspace
        self.rules: list[dict] = []
        self.current: dict | None = None
        self._proj_ids = [""]
        self.win = tk.Toplevel(master)
        self.win.title("周期任务")
        self.win.geometry("760x500")
        self.win.transient(master)
        self.win.grab_set()

        left = ttk.Frame(self.win)
        right = ttk.Frame(self.win)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.list = DataListbox(left)
        self.list.pack(fill=tk.BOTH, expand=True)
        self.list.bind("<<ListboxSelect>>", lambda e: self._load_row())
        ttk.Button(left, text="新建规则", command=self._new).pack(fill=tk.X, pady=4)

        form = ttk.Frame(right)
        form.pack(fill=tk.X)
        self.title = self._entry(form, 0, "标题")
        self.notes = self._entry(form, 1, "备注")
        ttk.Label(form, text="频率").grid(row=2, column=0, sticky="w")
        self.freq = ttk.Combobox(form, state="readonly", values=list(FREQ_LABELS.values()))
        self.freq.set("每天")
        self.freq.grid(row=2, column=1, sticky="ew")
        ttk.Label(form, text="间隔").grid(row=3, column=0, sticky="w")
        self.interval = ttk.Spinbox(form, from_=1, to=30, width=8)
        self.interval.set(1)
        self.interval.grid(row=3, column=1, sticky="w")
        self.time = self._entry(form, 4, "时刻", "09:00")
        self.start = self._entry(form, 5, "开始", today().isoformat())
        self.has_end = tk.BooleanVar(value=False)
        ttk.Checkbutton(form, text="结束日期", variable=self.has_end, command=self._toggle_end).grid(
            row=6, column=0, sticky="w"
        )
        self.end = ttk.Entry(form)
        self.end.insert(0, f"{today().year + 1}-{today().month:02d}-{today().day:02d}")
        self.end.grid(row=6, column=1, sticky="ew")
        ttk.Label(form, text="每月几号").grid(row=7, column=0, sticky="w")
        self.month_day = ttk.Spinbox(form, from_=1, to=31, width=8)
        self.month_day.set(today().day)
        self.month_day.grid(row=7, column=1, sticky="w")
        ttk.Label(form, text="周几").grid(row=8, column=0, sticky="nw")
        wd = ttk.Frame(form)
        wd.grid(row=8, column=1, sticky="w")
        self.weekdays = []
        for i, label in enumerate(WEEKDAYS):
            var = tk.BooleanVar(value=i < 5)
            ttk.Checkbutton(wd, text=label, variable=var).grid(row=i // 4, column=i % 4, sticky="w")
            self.weekdays.append(var)
        ttk.Label(form, text="关联项目").grid(row=9, column=0, sticky="w")
        self.project = ttk.Combobox(form, state="readonly")
        self.project.grid(row=9, column=1, sticky="ew")
        self.enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(form, text="启用", variable=self.enabled).grid(row=10, column=1, sticky="w")
        form.columnconfigure(1, weight=1)
        self._toggle_end()

        ttk.Button(right, text="保存当前规则", command=self._save).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="立即生成 60 天实例", command=self._generate).pack(fill=tk.X)
        ttk.Button(right, text="关闭", command=self.win.destroy).pack(fill=tk.X, pady=8)
        self._reload_projects()
        self._reload()

    def _entry(self, form, row, label, value="") -> ttk.Entry:
        ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=2)
        entry = ttk.Entry(form)
        entry.insert(0, value)
        entry.grid(row=row, column=1, sticky="ew", pady=2)
        return entry

    def _toggle_end(self) -> None:
        self.end.config(state=tk.NORMAL if self.has_end.get() else tk.DISABLED)

    def _reload_projects(self) -> None:
        labels = ["（无）"]
        self._proj_ids = [""]
        try:
            for proj in self.workspace.by_type(TYPE_PROJECT):
                labels.append(proj.get("name") or proj["_id"])
                self._proj_ids.append(proj["_id"])
        except CouchError:
            pass
        self.project["values"] = labels
        self.project.current(0)

    def show(self) -> None:
        self.win.wait_window()

    def _reload(self) -> None:
        try:
            self.workspace.reload()
            self.rules = self.workspace.all_recurring()
        except CouchError as exc:
            messagebox.showwarning("加载失败", str(exc), parent=self.win)
            self.rules = []
        items = []
        for rule in self.rules:
            flag = "开" if rule.get("enabled", True) else "停"
            items.append((f"[{flag}] {rule.get('title') or '未命名'}", rule))
        self.list.set_items(items)
        if self.rules:
            self.list.selection_set(0)
            self._load_row()
        else:
            self._new()

    def _new(self) -> None:
        self.current = {"enabled": True, "freq": FREQ_DAILY, "interval": 1}
        self.title.delete(0, tk.END)
        self.notes.delete(0, tk.END)
        self.freq.set("每天")
        self.interval.set(1)
        self.enabled.set(True)
        self.list.selection_clear(0, tk.END)

    def _load_row(self) -> None:
        rule = self.list.current()
        if not rule:
            return
        self.current = dict(rule)
        self.title.delete(0, tk.END)
        self.title.insert(0, rule.get("title") or "")
        self.notes.delete(0, tk.END)
        self.notes.insert(0, rule.get("notes") or "")
        self.freq.set(FREQ_LABELS.get(rule.get("freq") or FREQ_DAILY, "每天"))
        self.interval.set(int(rule.get("interval") or 1))
        self.time.delete(0, tk.END)
        self.time.insert(0, rule.get("timeOfDay") or "09:00")
        self.start.delete(0, tk.END)
        self.start.insert(0, str(rule.get("startDate") or today().isoformat())[:10])
        self.has_end.set(bool(rule.get("endDate")))
        if rule.get("endDate"):
            self.end.config(state=tk.NORMAL)
            self.end.delete(0, tk.END)
            self.end.insert(0, str(rule["endDate"])[:10])
        self._toggle_end()
        self.month_day.set(int(rule.get("byMonthDay") or today().day))
        selected = set(int(x) for x in (rule.get("byWeekday") or []))
        for i, var in enumerate(self.weekdays):
            var.set(i in selected if selected else i < 5)
        self.enabled.set(bool(rule.get("enabled", True)))
        pid = rule.get("projectId") or ""
        self.project.current(self._proj_ids.index(pid) if pid in self._proj_ids else 0)

    def _save(self) -> None:
        title = self.title.get().strip()
        if not title:
            messagebox.showwarning("校验", "请填写标题", parent=self.win)
            return
        freq_label = self.freq.get()
        freq = next((k for k, v in FREQ_LABELS.items() if v == freq_label), FREQ_DAILY)
        pidx = max(0, self.project.current())
        doc = dict(self.current or {})
        doc.update(
            {
                "title": title,
                "notes": self.notes.get().strip(),
                "freq": freq,
                "interval": int(self.interval.get() or 1),
                "timeOfDay": self.time.get().strip() or "09:00",
                "startDate": iso_date(parse_user_date(self.start.get()) or today()),
                "endDate": iso_date(parse_user_date(self.end.get())) if self.has_end.get() else None,
                "byMonthDay": int(self.month_day.get() or today().day),
                "byWeekday": [i for i, var in enumerate(self.weekdays) if var.get()],
                "enabled": self.enabled.get(),
                "projectId": self._proj_ids[pidx] if pidx < len(self._proj_ids) else "",
            }
        )
        try:
            save_recurring(self.workspace.require_client(), doc)
            self.workspace.reload()
            instantiate_window(self.workspace.require_client(), self.workspace.docs)
            self.workspace.reload()
        except CouchError as exc:
            messagebox.showwarning("保存失败", str(exc), parent=self.win)
            return
        self._reload()

    def _generate(self) -> None:
        try:
            n = instantiate_window(self.workspace.require_client(), self.workspace.docs)
            self.workspace.reload()
            messagebox.showinfo("周期任务", f"新生成 {n} 条实例", parent=self.win)
        except CouchError as exc:
            messagebox.showwarning("失败", str(exc), parent=self.win)
