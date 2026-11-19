from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")
WEEKDAYS_CN = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")


def now() -> datetime:
    return datetime.now(TZ)


def today() -> date:
    return now().date()


def day_start(d: date | None = None) -> datetime:
    d = d or today()
    return datetime.combine(d, time.min, tzinfo=TZ)


def day_end_exclusive(d: date | None = None) -> datetime:
    return day_start(d) + timedelta(days=1)


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if len(text) == 10 and text[4] == "-":
        d = date.fromisoformat(text)
        return datetime.combine(d, time.min, tzinfo=TZ)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)


def parse_date(value: str | None) -> date | None:
    dt = parse_dt(value)
    return dt.date() if dt else None


def iso_dt(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ).isoformat(timespec="seconds")


def iso_date(d: date | None) -> str | None:
    return d.isoformat() if d else None


def weekday_cn(d: date) -> str:
    return WEEKDAYS_CN[d.weekday()]


def parse_user_dt(text: str | None) -> datetime | None:
    raw = (text or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=TZ)
        except ValueError:
            continue
    return parse_dt(raw)


def parse_user_date(text: str | None) -> date | None:
    dt = parse_user_dt(text)
    return dt.date() if dt else None
