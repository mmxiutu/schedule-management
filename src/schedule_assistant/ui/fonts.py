from __future__ import annotations

import sys
from pathlib import Path

FONT_FILENAME = "赖江湖墨暖圆书827.ttf"


def lockscreen_font_path() -> Path | None:
    here = Path(__file__).resolve().parent.parent / "assets" / "fonts" / FONT_FILENAME
    paths = [here]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        root = Path(meipass)
        paths.extend(
            [
                root / "assets" / "fonts" / FONT_FILENAME,
                root / "schedule_assistant" / "assets" / "fonts" / FONT_FILENAME,
            ]
        )
    for path in paths:
        if path.is_file():
            return path
    return None
