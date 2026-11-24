"""System-tray host for Raspberry Pi OS (labwc).

The panel only shows StatusNotifier icons. pystray's X11 tray icon stays
invisible there, and the frozen app cannot import the system GI typelib.
This process is started with the system Python, which can.
"""

from __future__ import annotations

import os
import sys
import threading


def main() -> int:
    if len(sys.argv) < 2:
        print("missing icon path", file=sys.stderr)
        return 2
    icon_path = sys.argv[1]
    try:
        import gi

        gi.require_version("Gtk", "3.0")
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as AppIndicator
        from gi.repository import GLib, Gtk
    except Exception as exc:
        print(f"tray backend unavailable: {exc}", file=sys.stderr)
        return 1

    notify_mod = None
    try:
        gi.require_version("Notify", "0.7")
        from gi.repository import Notify

        Notify.init("日程管理助手")
        notify_mod = Notify
    except Exception as exc:
        print(f"notify unavailable: {exc}", file=sys.stderr)

    def emit(message: str) -> None:
        print(message, flush=True)

    def on_open(_item) -> None:
        emit("open")

    def on_quit(_item) -> None:
        emit("quit")
        Gtk.main_quit()

    icon_dir = os.path.dirname(icon_path)
    icon_name = os.path.splitext(os.path.basename(icon_path))[0]
    indicator = AppIndicator.Indicator.new(
        "schedule-assistant",
        icon_name,
        AppIndicator.IndicatorCategory.APPLICATION_STATUS,
    )
    indicator.set_icon_theme_path(icon_dir)
    indicator.set_icon_full(icon_name, "日程管理助手")
    indicator.set_title("日程管理助手")

    menu = Gtk.Menu()
    item_open = Gtk.MenuItem.new_with_label("打开主窗口")
    item_open.connect("activate", on_open)
    item_quit = Gtk.MenuItem.new_with_label("退出")
    item_quit.connect("activate", on_quit)
    menu.append(item_open)
    menu.append(item_quit)
    menu.show_all()
    indicator.set_menu(menu)
    indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)

    def handle(line: str) -> None:
        text = line.strip()
        if text == "stop":
            Gtk.main_quit()
            return
        if text.startswith("notify\t") and notify_mod is not None:
            parts = text.split("\t", 2)
            title = parts[1] if len(parts) > 1 else "日程管理助手"
            body = parts[2] if len(parts) > 2 else ""
            note = notify_mod.Notification.new(title, body, icon_path)
            note.show()

    def reader() -> None:
        for line in sys.stdin:
            GLib.idle_add(handle, line)
        GLib.idle_add(Gtk.main_quit)

    threading.Thread(target=reader, daemon=True).start()
    emit("ready")
    Gtk.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
