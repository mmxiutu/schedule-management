from __future__ import annotations

from datetime import date

from schedule_assistant.domain.clock import TZ

KIND_WORKDAY = "workday"
KIND_WEEKEND = "weekend"
KIND_HOLIDAY = "holiday"
KIND_MAKEUP = "makeup"

HOLIDAY_ZH = {
    "New Year's Day": "元旦",
    "Spring Festival": "春节",
    "Tomb-sweeping Day": "清明",
    "Labour Day": "劳动节",
    "Dragon Boat Festival": "端午",
    "National Day": "国庆节",
    "Mid-autumn Festival": "中秋",
    "Anti-Fascist 70th Day": "抗战胜利纪念日",
}


def holiday_label_zh(name: str | None) -> str | None:
    if not name:
        return None
    text = str(name)
    if text in HOLIDAY_ZH.values():
        return text
    mapped = HOLIDAY_ZH.get(text)
    if mapped:
        return mapped
    try:
        from chinese_calendar import Holiday

        for item in Holiday:
            if text in (item.value, getattr(item, "chinese", None)):
                return item.chinese
    except Exception:
        pass
    return text


def day_kind(d: date) -> tuple[str, str | None]:
    """Return (kind, Chinese label) for calendar coloring."""
    try:
        from chinese_calendar import get_holiday_detail, is_workday
    except Exception:
        if d.weekday() >= 5:
            return KIND_WEEKEND, None
        return KIND_WORKDAY, None

    try:
        on_holiday, name = get_holiday_detail(d)
        work = is_workday(d)
    except NotImplementedError:
        if d.weekday() >= 5:
            return KIND_WEEKEND, None
        return KIND_WORKDAY, None

    zh = holiday_label_zh(str(name) if name else None)
    if on_holiday and zh:
        return KIND_HOLIDAY, zh
    if d.weekday() >= 5:
        if work:
            return KIND_MAKEUP, "调休上班"
        return KIND_WEEKEND, None
    if not work:
        return KIND_HOLIDAY, zh or "休息"
    return KIND_WORKDAY, None


def is_shanghai_calendar_day(d: date) -> date:
    _ = TZ
    return d
