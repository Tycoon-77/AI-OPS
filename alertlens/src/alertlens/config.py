"""
Central configuration — reads from environment variables.
Falls back to pydantic-settings when available for .env file support.
Works with stdlib only so the pipeline runs before pip install.
"""
from __future__ import annotations

import os
from pathlib import Path


def _env(key: str, default: str) -> str:
    return os.environ.get(f"ALERTLENS_{key}", default)


def _load_dotenv(path: str = ".env") -> None:
    """Minimal .env loader — no external deps required."""
    dotenv = Path(path)
    if not dotenv.exists():
        return
    for line in dotenv.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


_load_dotenv()


class _Settings:
    db_path:           str   = _env("DB_PATH",           "data/alertlens.db")
    seed:              int   = int(_env("SEED",           "42"))
    api_url:           str   = _env("API_URL",            "http://localhost:8000")
    demo_mode:         int   = int(_env("DEMO_MODE",      "1"))
    redaction_salt:    str   = _env("REDACTION_SALT",     "change-me-local")
    surface_threshold: float = float(_env("SURFACE_THRESHOLD", "0.55"))
    pair_threshold:    float = float(_env("PAIR_THRESHOLD",    "0.60"))
    pair_window_min:   int   = int(_env("PAIR_WINDOW_MIN",     "10"))
    dedup_window_min:  int   = int(_env("DEDUP_WINDOW_MIN",    "5"))


settings = _Settings()
