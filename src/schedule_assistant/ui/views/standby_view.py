from __future__ import annotations

import sys
import tkinter as tk
from io import BytesIO
from tkinter import messagebox

from PIL import Image, ImageDraw, ImageFont

from schedule_assistant.domain.clock import now, weekday_cn
from schedule_assistant.services.weather import fetch_shanghai_weather
from schedule_assistant.ui.fonts import lockscreen_font_path

_FONT_CACHE: dict[int, ImageFont.FreeTypeFont] = {}


def _log(message: str) -> None:
    print(f"[standby] {message}", file=sys.stderr, flush=True)


def _font(size: int) -> ImageFont.FreeTypeFont:
    size = max(12, int(size))
    cached = _FONT_CACHE.get(size)
    if cached:
        return cached
    path = lockscreen_font_path()
    if not path:
        raise FileNotFoundError("锁屏字体未找到")
    try:
        font = ImageFont.truetype(str(path), size)
    except OSError:
        font = ImageFont.truetype(BytesIO(path.read_bytes()), size)
    _FONT_CACHE[size] = font
    return font


def _fit_font(text: str, max_w: int, max_h: int, multiline: bool = False) -> ImageFont.FreeTypeFont:
    lo, hi = 16, max(16, min(max_w, max_h, 420))
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


def _to_tk_photo(img: Image.Image, master: tk.Misc) -> tk.PhotoImage:
    buf = BytesIO()
    img.save(buf, format="PPM")
    return tk.PhotoImage(data=buf.getvalue(), master=master)


class StandbyView(tk.Toplevel):
    def __init__(self, master, on_close):
        super().__init__(master)
        self.on_close = on_close
        self.withdraw()
        self.configure(bg="#000000")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Escape>", lambda e: self.on_close())
        self.canvas = tk.Canvas(self, bg="#000000", highlightthickness=0, bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", lambda e: self.on_close())
        self.bind("<Button-1>", lambda e: self.on_close())
        self._photo: tk.PhotoImage | None = None
        self._weather = "正在获取上海天气…"
        self._tick_job = None
        self._weather_job = None
        self._screen = (1280, 720)

    def start(self) -> None:
        try:
            _font(32)
            sw = max(self.winfo_screenwidth(), 1280)
            sh = max(self.winfo_screenheight(), 720)
            self._screen = (sw, sh)
            self.geometry(f"{sw}x{sh}+0+0")
            self.deiconify()
            self.lift()
            self.update_idletasks()
            # Raspberry Pi / Wayland 上 -fullscreen 常把子控件尺寸弄成 0，改为铺满屏幕几何。
            if not sys.platform.startswith("linux"):
                try:
                    self.attributes("-fullscreen", True)
                except tk.TclError:
                    pass
            try:
                self.attributes("-topmost", True)
            except tk.TclError:
                pass
            self.focus_force()
            self._paint()
            self._tick_job = self.after(1000, self._tick)
            self.after(300, self._load_weather)
        except Exception as exc:
            _log(f"start failed: {exc}")
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
        except Exception as exc:
            _log(f"weather failed: {exc}")
            self._weather = "天气暂不可用"
        self._paint()
        self._weather_job = self.after(15 * 60 * 1000, self._load_weather)

    def _paint(self) -> None:
        sw, sh = self._screen
        win_w = self.winfo_width()
        win_h = self.winfo_height()
        if win_w >= 320:
            sw = win_w
        if win_h >= 240:
            sh = win_h
        left_w = sw * 2 // 3
        right_w = sw - left_w
        half_h = sh // 2
        t = now()
        clock = t.strftime("%H:%M")
        date_text = f"{t.strftime('%m-%d')}\n{weekday_cn(t.date())}"
        try:
            img = Image.new("RGB", (sw, sh), "#000000")
            draw = ImageDraw.Draw(img)
            self._draw_block(draw, clock, 0, 0, left_w, sh, False, 0.90)
            self._draw_block(draw, date_text, left_w, 0, right_w, half_h, True, 0.80)
            self._draw_block(draw, self._weather, left_w, half_h, right_w, sh - half_h, True, 0.78)
            photo = _to_tk_photo(img, self)
        except Exception as exc:
            _log(f"paint failed, fallback text: {exc}")
            self._paint_tk_text(sw, sh, left_w, half_h, clock, date_text)
            return
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=photo, anchor=tk.NW)
        self._photo = photo

    def _draw_block(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x: int,
        y: int,
        w: int,
        h: int,
        multiline: bool,
        ratio: float,
    ) -> None:
        max_w, max_h = max(20, int(w * ratio)), max(20, int(h * ratio))
        font = _fit_font(text, max_w, max_h, multiline=multiline)
        if multiline:
            bbox = draw.multiline_textbbox((0, 0), text, font=font, align="center")
        else:
            bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        px = x + (w - tw) // 2 - bbox[0]
        py = y + (h - th) // 2 - bbox[1]
        if multiline:
            draw.multiline_text((px, py), text, font=font, fill="#FFFFFF", align="center")
        else:
            draw.text((px, py), text, font=font, fill="#FFFFFF")

    def _paint_tk_text(self, sw: int, sh: int, left_w: int, half_h: int, clock: str, date_text: str) -> None:
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, sw, sh, fill="#000000", outline="")
        clock_size = max(48, min(left_w // 4, sh // 3))
        date_size = max(22, min((sw - left_w) // 6, half_h // 4))
        self.canvas.create_text(
            left_w // 2,
            sh // 2,
            text=clock,
            fill="#FFFFFF",
            font=("Noto Sans CJK SC", clock_size, "bold"),
            anchor=tk.CENTER,
        )
        self.canvas.create_text(
            left_w + (sw - left_w) // 2,
            half_h // 2,
            text=date_text,
            fill="#FFFFFF",
            font=("Noto Sans CJK SC", date_size),
            anchor=tk.CENTER,
            justify=tk.CENTER,
        )
        self.canvas.create_text(
            left_w + (sw - left_w) // 2,
            half_h + (sh - half_h) // 2,
            text=self._weather,
            fill="#FFFFFF",
            font=("Noto Sans CJK SC", max(18, date_size - 8)),
            anchor=tk.CENTER,
            width=max(80, sw - left_w - 24),
        )
