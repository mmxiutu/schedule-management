from __future__ import annotations

import tkinter as tk
from typing import Any


class DataListbox(tk.Listbox):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("exportselection", False)
        super().__init__(master, **kwargs)
        self._data: list[Any] = []

    def set_items(self, items: list[tuple[str, Any]]) -> None:
        self.delete(0, tk.END)
        self._data = []
        for text, data in items:
            self.insert(tk.END, text)
            self._data.append(data)

    def current(self) -> Any:
        sel = self.curselection()
        if not sel:
            return None
        idx = sel[0]
        if 0 <= idx < len(self._data):
            return self._data[idx]
        return None

    def all_data(self) -> list[Any]:
        return list(self._data)
