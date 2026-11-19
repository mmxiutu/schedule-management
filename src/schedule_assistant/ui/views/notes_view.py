from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from schedule_assistant.db.client import CouchError
from schedule_assistant.db.repo import save_note
from schedule_assistant.ui.widgets.listbox import DataListbox
from schedule_assistant.workspace import Workspace

UNCATEGORIZED = "未分类"


class NotesView(ttk.Frame):
    def __init__(self, master, workspace: Workspace):
        super().__init__(master)
        self.workspace = workspace
        self.current: dict | None = None
        self._filter_busy = False

        left = ttk.Frame(self)
        right = ttk.Frame(self)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(left, text="分类筛选").pack(anchor="w")
        self.filter = ttk.Combobox(left, state="readonly")
        self.filter.pack(fill=tk.X)
        self.filter.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        self.list = DataListbox(left)
        self.list.pack(fill=tk.BOTH, expand=True, pady=4)
        self.list.bind("<<ListboxSelect>>", lambda e: self._load())
        ttk.Button(left, text="新建记事", command=self._new).pack(fill=tk.X)

        self.title = ttk.Entry(right)
        self.title.pack(fill=tk.X, pady=(0, 4))
        self.category = ttk.Combobox(right)
        self.category.pack(fill=tk.X, pady=(0, 4))
        self.content = tk.Text(right, wrap=tk.WORD, height=12)
        self.content.pack(fill=tk.BOTH, expand=True)
        ttk.Button(right, text="保存", command=self._save).pack(fill=tk.X, pady=4)

    def _categories(self) -> list[str]:
        try:
            settings = self.workspace.settings_doc()
            return list(settings.get("noteCategories") or [])
        except CouchError:
            return []

    def refresh(self) -> None:
        if self._filter_busy:
            return
        cats = self._categories()
        current_filter = self.filter.get() or "全部"
        self._filter_busy = True
        values = ["全部", UNCATEGORIZED, *cats]
        self.filter["values"] = values
        if current_filter not in values:
            current_filter = "全部"
        self.filter.set(current_filter)
        self.category["values"] = [""] + cats
        self._filter_busy = False

        try:
            notes = self.workspace.all_notes()
        except Exception as exc:
            self.list.set_items([(str(exc), None)])
            return
        selected = self.filter.get()
        items = []
        for note in notes:
            cat = note.get("category") or ""
            if selected == UNCATEGORIZED and cat:
                continue
            if selected not in ("全部", "", UNCATEGORIZED) and cat != selected:
                continue
            items.append((f"{note.get('title') or '(无标题)'}  ·  {note.get('createdAt') or ''}", note))
        self.list.set_items(items)

    def _new(self) -> None:
        self.current = {}
        self.title.delete(0, tk.END)
        self.content.delete("1.0", tk.END)
        self.category.set("")
        self.list.selection_clear(0, tk.END)

    def _load(self) -> None:
        note = self.list.current()
        if not note:
            return
        self.current = dict(note)
        self.title.delete(0, tk.END)
        self.title.insert(0, note.get("title") or "")
        self.content.delete("1.0", tk.END)
        self.content.insert("1.0", note.get("content") or "")
        self.category.set(note.get("category") or "")

    def _save(self) -> None:
        content = self.content.get("1.0", tk.END).rstrip("\n")
        if not content.strip():
            messagebox.showwarning("校验", "内容不能为空", parent=self)
            return
        doc = dict(self.current or {})
        doc["title"] = self.title.get()
        doc["content"] = content
        doc["category"] = self.category.get().strip()
        try:
            self.current = save_note(self.workspace.require_client(), doc)
            self.workspace.reload()
        except (CouchError, ValueError) as exc:
            messagebox.showwarning("保存失败", str(exc), parent=self)
            return
        self.refresh()
