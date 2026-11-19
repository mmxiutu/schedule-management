from __future__ import annotations

import json
import time
from pathlib import Path

import jwt
import requests

from schedule_assistant.app_paths import config_dir

# 和风天气实时天气: https://dev.qweather.com/docs/api/weather/weather-current/
QWEATHER_HOST = "mv49vk5p7y.re.qweatherapi.com"
SHANGHAI_LAT = 31.23
SHANGHAI_LON = 121.47

DEFAULT_JWT = {
    "kid": "KAB6RD4XWV",
    "iss": "Q90D00C701",
    "sub": "45KX2DDRQG",
    "private_key": (
        "-----BEGIN PRIVATE KEY-----\n"
        "MC4CAQAwBQYDK2VwBCIEII0IZ1H4LjRWGxKzm4s6OPF9vkTlBuO2dpof94MwIDft\n"
        "-----END PRIVATE KEY-----"
    ),
}


def _qweather_path() -> Path:
    return config_dir() / "qweather.json"


def _jwt_fields() -> dict:
    cfg = dict(DEFAULT_JWT)
    path = _qweather_path()
    if path.exists():
        cfg.update(json.loads(path.read_text(encoding="utf-8")))
    return cfg


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
    token = _build_jwt(_jwt_fields())
    url = f"https://{QWEATHER_HOST}/weather/v1/current/{SHANGHAI_LAT}/{SHANGHAI_LON}"
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
