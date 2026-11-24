from __future__ import annotations

import os
import sys
import traceback
import tkinter as tk
from tkinter import messagebox

from schedule_assistant.app_paths import config_dir
from schedule_assistant.resources import install_desktop_icon
from schedule_assistant.ui.main_window import MainWindow
from schedule_assistant.workspace import Workspace


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def _acquire_lock() -> bool:
    path = config_dir() / "instance.pid"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            old = int(path.read_text(encoding="utf-8").strip())
        except ValueError:
            old = 0
        if _pid_alive(old):
            return False
    path.write_text(str(os.getpid()), encoding="utf-8")
    return True


def main() -> None:
    root = tk.Tk(className="ScheduleAssistant")
    root.withdraw()
    if not _acquire_lock():
        messagebox.showinfo("日程管理助手", "程序已在运行。")
        root.destroy()
        return
    try:
        install_desktop_icon()
        workspace = Workspace()
        root.deiconify()
        MainWindow(root, workspace)
        if workspace.last_error:
            messagebox.showwarning(
                "CouchDB 连接",
                f"未能连接到数据库。\n{workspace.last_error}\n\n请点击顶部「设置」检查地址并测试连接。",
            )
        root.mainloop()
    except Exception as exc:
        log = config_dir() / "error.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(traceback.format_exc(), encoding="utf-8")
        messagebox.showerror("日程管理助手", f"启动失败：{exc}\n详情已写入:\n{log}")
        raise


if __name__ == "__main__":
    main()
