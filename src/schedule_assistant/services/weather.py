from __future__ import annotations

import json
import time
from pathlib import Path

import jwt
import requests

from schedule_assistant.app_paths import config_dir

# 和风天气实时天气: https://dev.qweather.com/docs/api/weather/weather-current/
SHANGHAI_LAT = 31.23
SHANGHAI_LON = 121.47


def qweather_path() -> Path:
    return config_dir() / "qweather.json"


def _load_qweather() -> dict:
    path = qweather_path()
    if not path.exists():
        raise ValueError(f"缺少和风天气配置：{path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("和风天气配置格式无效")
    return data


def _build_jwt(cfg: dict) -> str:
    private_key = (cfg.get("private_key") or "").strip()
    iss = (cfg.get("iss") or "").strip()
    sub = (cfg.get("sub") or "").strip()
    kid = (cfg.get("kid") or "").strip()
    if not private_key or not iss or not sub or not kid:
        raise ValueError("和风天气 JWT 配置不完整")
    now = int(time.time())
    payload = {"iss": iss, "sub": sub, "iat": now - 30, "exp": now + 900}
    headers = {"kid": kid}
    return jwt.encode(payload, private_key, algorithm="EdDSA", headers=headers)


def fetch_shanghai_weather(timeout: float = 8.0) -> str:
    cfg = _load_qweather()
    host = (cfg.get("host") or "").strip().rstrip("/")
    if not host:
        raise ValueError("和风天气 host 未配置")
    lat = cfg.get("lat", SHANGHAI_LAT)
    lon = cfg.get("lon", SHANGHAI_LON)
    token = _build_jwt(cfg)
    url = f"https://{host}/weather/v1/current/{lat}/{lon}"
    resp = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        params={"lang": "zh", "localTime": "true"},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    condition = (data.get("condition") or {}).get("text") or "天气"
    temp = (data.get("temperature") or {}).get("value")
    if temp is None:
        raise ValueError("missing temperature")
    return f"上海  {condition}  {float(temp):.0f}°C"
