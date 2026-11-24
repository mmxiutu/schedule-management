from __future__ import annotations

import sys
from pathlib import Path

FONT_FILENAME = "ljhmnys.ttf"
ICON_FILENAME = "orange.png"


def _search(relative: Path) -> Path | None:
    roots = [Path(__file__).resolve().parent / "assets"]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        root = Path(meipass)
        roots.extend(
            [
                root / "assets",
                root / "schedule_assistant" / "assets",
            ]
        )
    for base in roots:
        path = base / relative
        if path.is_file():
            return path
    return None


def lockscreen_font_path() -> Path | None:
    return _search(Path("fonts") / FONT_FILENAME)


def app_icon_path() -> Path | None:
    return _search(Path("images") / ICON_FILENAME)


def linux_tray_host_path() -> Path | None:
    return _search(Path("linux_tray_host.py"))


def install_desktop_icon() -> None:
    """Copy the window icon where labwc / wf-panel look up the app id."""
    if not sys.platform.startswith("linux"):
        return
    src = app_icon_path()
    if src is None:
        return
    dest_dir = Path.home() / ".local/share/icons/hicolor/256x256/apps"
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        data = src.read_bytes()
        for name in (
            "ScheduleAssistant.png",
            "Scheduleassistant.png",
            "scheduleassistant.png",
            "scheduleAssistant.png",
        ):
            target = dest_dir / name
            if target.is_file() and target.stat().st_size == len(data):
                continue
            target.write_bytes(data)
    except OSError:
        pass
