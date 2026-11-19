from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from schedule_assistant.app_paths import ConnectionConfig
from schedule_assistant.db.client import CouchError
from schedule_assistant.db.repo import get_settings, save_settings
from schedule_assistant.ui.theme import (
    COLOR_HOLIDAY,
    COLOR_MAKEUP,
    COLOR_PROJECT,
    COLOR_RECURRING,
    COLOR_WEEKEND,
    COLOR_WORKDAY,
)
from schedule_assistant.ui.widgets.listbox import DataListbox
from schedule_assistant.workspace import Workspace


class SettingsDialog:
    def __init__(self, master, workspace: Workspace):
        self.workspace = workspace
        self.result = False
        self.win = tk.Toplevel(master)
        self.win.title("设置")
        self.win.geometry("520x520")
        self.win.transient(master)
        self.win.grab_set()

        form = ttk.Frame(self.win)
        form.pack(fill=tk.X, padx=12, pady=8)
        self.url = self._row(form, 0, "CouchDB 地址", workspace.connection.url)
        self.user = self._row(form, 1, "用户名", workspace.connection.user)
        self.password = self._row(form, 2, "密码", workspace.connection.password, show="*")
        self.db = self._row(form, 3, "数据库名", workspace.connection.db)

        ttk.Button(self.win, text="测试连接", command=self._ping).pack(anchor="w", padx=12)
        self.ping_label = ttk.Label(self.win, wraplength=480)
        self.ping_label.pack(anchor="w", padx=12, pady=4)

        ttk.Label(self.win, text="记事本分类（空 = 未分类）").pack(anchor="w", padx=12)
        self.categories = DataListbox(self.win, height=6)
        self.categories.pack(fill=tk.X, padx=12)
        cat_row = ttk.Frame(self.win)
        cat_row.pack(fill=tk.X, padx=12, pady=4)
        self.cat_input = ttk.Entry(cat_row)
        self.cat_input.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(cat_row, text="添加分类", command=self._add_category).pack(side=tk.LEFT, padx=4)
        ttk.Button(cat_row, text="删除所选", command=self._del_category).pack(side=tk.LEFT)

        try:
            settings = get_settings(workspace.client) if workspace.client else {"noteCategories": []}
        except CouchError:
            settings = {"noteCategories": []}
        self.categories.set_items([(str(n), str(n)) for n in settings.get("noteCategories") or []])

        legend = ttk.Frame(self.win)
        legend.pack(fill=tk.X, padx=12, pady=8)
        ttk.Label(legend, text="月历色标（色弱友好，只读）").pack(anchor="w")
        chips = ttk.Frame(legend)
        chips.pack(anchor="w")
        for text, bg in [
            ("普通工作日", COLOR_WORKDAY),
            ("周末", COLOR_WEEKEND),
            ("法定节假日", COLOR_HOLIDAY),
            ("调休上班", COLOR_MAKEUP),
            ("周期任务", COLOR_RECURRING),
            ("项目标记", COLOR_PROJECT),
        ]:
            tk.Label(chips, text=f" {text} ", bg=bg).pack(side=tk.LEFT, padx=3)

        btns = ttk.Frame(self.win)
        btns.pack(pady=8)
        ttk.Button(btns, text="确定", command=self._save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="取消", command=self.win.destroy).pack(side=tk.LEFT)

    def _row(self, form, row, label, value, show=None) -> ttk.Entry:
        ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=3)
        entry = ttk.Entry(form, show=show or "")
        entry.insert(0, value)
        entry.grid(row=row, column=1, sticky="ew", pady=3)
        form.columnconfigure(1, weight=1)
        return entry

    def show(self) -> bool:
        self.win.wait_window()
        return self.result

    def _cfg(self) -> ConnectionConfig:
        return ConnectionConfig(
            url=self.url.get().strip(),
            user=self.user.get().strip(),
            password=self.password.get(),
            db=self.db.get().strip(),
        )

    def _ping(self) -> None:
        try:
            self.ping_label.config(text=self.workspace.ping_preview(self._cfg()))
        except Exception as exc:
            self.ping_label.config(text=f"连接失败：{exc}")

    def _add_category(self) -> None:
        name = self.cat_input.get().strip()
        if not name:
            return
        existing = [c for c in self.categories.all_data() if c]
        if name not in existing:
            existing.append(name)
            self.categories.set_items([(c, c) for c in existing])
        self.cat_input.delete(0, tk.END)

    def _del_category(self) -> None:
        cur = self.categories.current()
        if cur is None:
            return
        remain = [c for c in self.categories.all_data() if c != cur]
        self.categories.set_items([(c, c) for c in remain])

    def _save(self) -> None:
        ok = self.workspace.connect(self._cfg())
        if not ok:
            messagebox.showwarning("连接失败", self.workspace.last_error or "无法连接 CouchDB", parent=self.win)
            return
        cats = [c for c in self.categories.all_data() if c]
        try:
            settings = get_settings(self.workspace.require_client())
            settings["noteCategories"] = cats
            save_settings(self.workspace.require_client(), settings)
        except CouchError as exc:
            messagebox.showwarning("保存设置失败", str(exc), parent=self.win)
            return
        self.result = True
        self.win.destroy()
