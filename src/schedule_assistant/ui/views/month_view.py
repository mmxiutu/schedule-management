from __future__ import annotations

from datetime import date, timedelta
import tkinter as tk
from tkinter import messagebox, ttk

from schedule_assistant.db.client import CouchError
from schedule_assistant.db.models import KIND_RECURRING
from schedule_assistant.db.repo import save_note
from schedule_assistant.domain.clock import parse_dt, today
from schedule_assistant.domain.holidays import KIND_WORKDAY, day_kind
from schedule_assistant.domain.time_filters import monday_of, three_week_days, undated_open_tasks
from schedule_assistant.ui.theme import (
    COLOR_PROJECT,
    COLOR_RECURRING,
    COLOR_TEXT_ON_DARK,
    COLOR_TEXT_ON_LIGHT,
    COLOR_TODAY_BG,
    COLOR_TODAY_BORDER,
    KIND_COLORS,
    KIND_LABELS,
)
from schedule_assistant.ui.widgets.listbox import DataListbox
from schedule_assistant.workspace import Workspace

WEEK_HEADERS = ["一", "二", "三", "四", "五", "六", "日"]


class DayCell(tk.Frame):
    def __init__(self, master, on_click):
        super().__init__(
            master,
            bd=0,
            highlightthickness=3,
            highlightbackground="#cccccc",
            cursor="hand2",
        )
        self.day: date | None = None
        self.on_click = on_click
        self.head = tk.Label(self, anchor="w", cursor="hand2", wraplength=80)
        self.body = tk.Label(self, anchor="nw", justify=tk.LEFT, wraplength=80, cursor="hand2")
        self.head.pack(fill=tk.X, padx=3, pady=(3, 0))
        self.body.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        self.body.bind("<Configure>", self._fit_wrap)
        for widget in (self, self.head, self.body):
            widget.bind("<Button-1>", self._clicked)

    def _fit_wrap(self, event) -> None:
        self.body.config(wraplength=max(40, event.width - 4))

    def _clicked(self, _event) -> None:
        if self.day and self.on_click:
            self.on_click(self.day)

    def set_day(self, d: date, kind: str, label: str | None, lines: list[str], is_today: bool) -> None:
        self.day = d
        bg = KIND_COLORS.get(kind, "#FFFFFF")
        if is_today and kind == KIND_WORKDAY:
            bg = COLOR_TODAY_BG
        fg = (
            COLOR_TEXT_ON_LIGHT
            if kind in (KIND_WORKDAY,) or bg in ("#FFFFFF", "#F0E442", "#E69F00", COLOR_TODAY_BG)
            else COLOR_TEXT_ON_DARK
        )
        extra = f" {label}" if label else ""
        mark = " · 今天" if is_today else ""
        self.head.config(text=f"{d.month:02d}-{d.day:02d}{extra}{mark}", bg=bg, fg=fg)
        self.body.config(text="\n".join(lines) or " ", bg=bg, fg=fg)
        border = COLOR_TODAY_BORDER if is_today else "#cccccc"
        self.config(
            bg=bg,
            highlightbackground=border,
            highlightcolor=border,
            highlightthickness=3,
        )


class MonthView(ttk.Frame):
    def __init__(self, master, workspace: Workspace, on_edit_task, on_new_for_day):
        super().__init__(master)
        self.workspace = workspace
        self.on_edit_task = on_edit_task
        self.on_new_for_day = on_new_for_day
        self.page_monday = monday_of(today())

        ttk.Label(self, text="未设置截止日期的任务").pack(anchor="w")
        self.summary = DataListbox(self, height=3)
        self.summary.pack(fill=tk.X)
        self.summary.bind("<Double-Button-1>", lambda e: self._edit(self.summary.current()))

        nav = ttk.Frame(self)
        nav.pack(fill=tk.X, pady=4)
        for text, handler in [
            ("上一页", lambda: self._shift(timedelta(days=-21))),
            ("上周", lambda: self._shift(timedelta(days=-7))),
            ("回到今天", self._go_today),
            ("下周", lambda: self._shift(timedelta(days=7))),
            ("下一页", lambda: self._shift(timedelta(days=21))),
        ]:
            ttk.Button(nav, text=text, command=handler).pack(side=tk.LEFT, padx=2)
        self.range_label = ttk.Label(nav)
        self.range_label.pack(side=tk.LEFT, padx=8)

        legend = ttk.Frame(self)
        legend.pack(fill=tk.X, pady=4)
        for key, name in KIND_LABELS.items():
            tk.Label(legend, text=f" {name} ", bg=KIND_COLORS[key], fg="#000").pack(side=tk.LEFT, padx=3)
        tk.Label(legend, text=" 周期任务 ", bg=COLOR_RECURRING).pack(side=tk.LEFT, padx=3)
        tk.Label(legend, text=" 项目标记 ", bg=COLOR_PROJECT).pack(side=tk.LEFT, padx=3)

        center = ttk.Frame(self)
        center.pack(fill=tk.BOTH, expand=True)
        grid_host = ttk.Frame(center)
        grid_host.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right = ttk.Frame(center, width=260)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)

        grid_host.rowconfigure(0, weight=0)
        for i, name in enumerate(WEEK_HEADERS):
            ttk.Label(grid_host, text=name, anchor="center").grid(row=0, column=i, sticky="nsew")
            grid_host.columnconfigure(i, weight=1, uniform="weekday", minsize=0)
        self.cells: list[DayCell] = []
        for r in range(3):
            grid_host.rowconfigure(r + 1, weight=1, uniform="weekrow")
            for c in range(7):
                cell = DayCell(grid_host, self.on_new_for_day)
                cell.grid(row=r + 1, column=c, sticky="nsew", padx=2, pady=2)
                self.cells.append(cell)

        ttk.Label(right, text="快速记录").pack(anchor="w")
        self.quick = tk.Text(right, wrap=tk.WORD, width=28)
        self.quick.pack(fill=tk.BOTH, expand=True, pady=4)
        ttk.Button(right, text="保存到记事本", command=self._save_note).pack(fill=tk.X)

    def _shift(self, delta: timedelta) -> None:
        self.page_monday = self.page_monday + delta
        self.refresh()

    def _go_today(self) -> None:
        self.page_monday = monday_of(today())
        self.refresh()

    def _edit(self, task: dict | None) -> None:
        if task:
            self.on_edit_task(task)

    def _save_note(self) -> None:
        text = self.quick.get("1.0", tk.END).rstrip("\n")
        if not text.strip():
            messagebox.showinfo("记事本", "请先输入内容", parent=self)
            return
        try:
            save_note(self.workspace.require_client(), {"content": text, "title": "", "category": ""})
            self.workspace.reload()
        except (CouchError, ValueError) as exc:
            messagebox.showwarning("保存失败", str(exc), parent=self)
            return
        self.quick.delete("1.0", tk.END)
        messagebox.showinfo("记事本", "已保存", parent=self)

    def refresh(self) -> None:
        days = three_week_days(self.page_monday)
        self.range_label.config(text=f"{days[0].isoformat()}  ~  {days[-1].isoformat()}")
        try:
            tasks = self.workspace.all_tasks()
            projects = self.workspace.projects_by_id()
        except Exception as exc:
            self.summary.set_items([(str(exc), None)])
            return
        self.summary.set_items(
            [(task.get("title") or "(无标题)", task) for task in undated_open_tasks(tasks)]
        )
        by_day: dict[date, list[dict]] = {d: [] for d in days}
        for task in tasks:
            due = parse_dt(task.get("dueAt"))
            start = parse_dt(task.get("startAt"))
            if due and due.date() in by_day:
                by_day[due.date()].append(task)
            elif start and start.date() in by_day:
                by_day[start.date()].append(task)
        today_d = today()
        for cell, d in zip(self.cells, days):
            kind, label = day_kind(d)
            lines = []
            for task in by_day[d]:
                prefix = ""
                if task.get("kind") == KIND_RECURRING:
                    prefix = "● "
                if task.get("projectId") and task["projectId"] in projects:
                    prefix += "■ "
                lines.append(f"{prefix}{task.get('title') or ''}")
            cell.set_day(d, kind, label, lines[:6], d == today_d)
