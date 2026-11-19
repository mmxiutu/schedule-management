from __future__ import annotations

import tkinter as tk


def center_on_parent(win: tk.Toplevel, width: int, height: int, parent: tk.Misc | None = None) -> None:
    win.update_idletasks()
    if parent is not None:
        parent.update_idletasks()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = max(parent.winfo_width(), 1)
        ph = max(parent.winfo_height(), 1)
        x = px + (pw - width) // 2
        y = py + (ph - height) // 2
    else:
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = (sw - width) // 2
        y = (sh - height) // 2
    x = max(0, x)
    y = max(0, y)
    win.geometry(f"{width}x{height}+{x}+{y}")


def bind_escape_close(win: tk.Toplevel) -> None:
    win.bind("<Escape>", lambda _e: win.destroy())
    win.focus_set()
