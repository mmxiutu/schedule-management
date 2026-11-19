from __future__ import annotations

import tkinter as tk
from io import BytesIO
from tkinter import messagebox

from PIL import Image, ImageDraw, ImageFont, ImageTk

from schedule_assistant.domain.clock import now, weekday_cn
from schedule_assistant.services.weather import fetch_shanghai_weather
from schedule_assistant.ui.fonts import lockscreen_font_path

_FONT_BYTES: bytes | None = None
_FONT_CACHE: dict[int, ImageFont.FreeTypeFont] = {}


def _font_bytes() -> bytes | None:
    global _FONT_BYTES
    if _FONT_BYTES is not None:
        return _FONT_BYTES
    path = lockscreen_font_path()
    if not path:
        return None
    _FONT_BYTES = path.read_bytes()
    return _FONT_BYTES


def _font(size: int) -> ImageFont.FreeTypeFont:
    size = max(12, int(size))
    cached = _FONT_CACHE.get(size)
    if cached:
        return cached
    data = _font_bytes()
    if not data:
        raise FileNotFoundError("锁屏字体未找到")
    font = ImageFont.truetype(BytesIO(data), size)
    _FONT_CACHE[size] = font
    return font


def _fit_font(text: str, max_w: int, max_h: int, multiline: bool = False) -> ImageFont.FreeTypeFont:
    lo, hi = 16, max(16, min(max_w, max_h, 520))
    best = 16
    dummy = Image.new("RGB", (8, 8))
    draw = ImageDraw.Draw(dummy)
    while lo <= hi:
        mid = (lo + hi) // 2
        font = _font(mid)
        if multiline:
            bbox = draw.multiline_textbbox((0, 0), text, font=font, align="center")
        else:
            bbox = draw.textbbox((0, 0), text, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if w <= max_w and h <= max_h:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return _font(best)


class StandbyView(tk.Toplevel):
    def __init__(self, master, on_close):
        super().__init__(master)
        self.on_close = on_close
        self.withdraw()
        self.configure(bg="#000000")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Escape>", lambda e: self.on_close())
        self.clock_label = tk.Label(self, bg="#000000", bd=0)
        self.date_label = tk.Label(self, bg="#000000", bd=0)
        self.weather_label = tk.Label(self, bg="#000000", bd=0)
        self.clock_label.place(relx=0, rely=0, relwidth=2 / 3, relheight=1)
        self.date_label.place(relx=2 / 3, rely=0, relwidth=1 / 3, relheight=0.5)
        self.weather_label.place(relx=2 / 3, rely=0.5, relwidth=1 / 3, relheight=0.5)
        for widget in (self, self.clock_label, self.date_label, self.weather_label):
            widget.bind("<Button-1>", lambda e: self.on_close())
        self._photos: list[ImageTk.PhotoImage] = []
        self._weather = "正在获取上海天气…"
        self._tick_job = None
        self._weather_job = None

    def start(self) -> None:
        try:
            _font(24)
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            self.geometry(f"{sw}x{sh}+0+0")
            self.deiconify()
            self.lift()
            try:
                self.attributes("-fullscreen", True)
            except tk.TclError:
                pass
            try:
                self.attributes("-topmost", True)
            except tk.TclError:
                pass
            self.focus_force()
            self.after(80, self._paint)
            self._tick_job = self.after(1000, self._tick)
            self.after(200, self._load_weather)
        except Exception as exc:
            messagebox.showerror("待机", f"无法进入待机：{exc}", parent=self.master)
            self.on_close()

    def stop(self) -> None:
        if self._tick_job:
            try:
                self.after_cancel(self._tick_job)
            except Exception:
                pass
            self._tick_job = None
        if self._weather_job:
            try:
                self.after_cancel(self._weather_job)
            except Exception:
                pass
            self._weather_job = None
        try:
            self.attributes("-fullscreen", False)
            self.attributes("-topmost", False)
        except tk.TclError:
            pass
        self.withdraw()

    def _tick(self) -> None:
        self._paint()
        self._tick_job = self.after(1000, self._tick)

    def _load_weather(self) -> None:
        try:
            self._weather = fetch_shanghai_weather()
        except Exception:
            self._weather = "天气暂不可用"
        self._paint()
        self._weather_job = self.after(15 * 60 * 1000, self._load_weather)

    def _paint(self) -> None:
        t = now()
        self._set_image(self.clock_label, t.strftime("%H:%M"), False, 0.90)
        self._set_image(self.date_label, f"{t.strftime('%m-%d')}\n{weekday_cn(t.date())}", True, 0.80)
        self._set_image(self.weather_label, self._weather, True, 0.80)

    def _set_image(self, label: tk.Label, text: str, multiline: bool, ratio: float) -> None:
        w = max(label.winfo_width(), int(self.winfo_width() * (2 / 3 if label is self.clock_label else 1 / 3)))
        h = max(label.winfo_height(), int(self.winfo_height() * (1 if label is self.clock_label else 0.5)))
        if w < 80 or h < 80:
            return
        max_w, max_h = int(w * ratio), int(h * ratio)
        try:
            font = _fit_font(text, max_w, max_h, multiline=multiline)
            img = Image.new("RGB", (w, h), "#000000")
            draw = ImageDraw.Draw(img)
            if multiline:
                bbox = draw.multiline_textbbox((0, 0), text, font=font, align="center")
            else:
                bbox = draw.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x = (w - tw) // 2 - bbox[0]
            y = (h - th) // 2 - bbox[1]
            if multiline:
                draw.multiline_text((x, y), text, font=font, fill="#FFFFFF", align="center")
            else:
                draw.text((x, y), text, font=font, fill="#FFFFFF")
            photo = ImageTk.PhotoImage(img, master=self)
        except Exception:
            return
        label.config(image=photo)
        label.image = photo
        self._photos.append(photo)
        self._photos = self._photos[-8:]
