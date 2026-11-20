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
