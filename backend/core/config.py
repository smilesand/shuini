from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
    "http://localhost:5176",
    "http://127.0.0.1:5176",
    "http://1.117.73.146",
)


def _default_db_path() -> str:
    if getattr(sys, "frozen", False):
        return os.path.join(os.getcwd(), "data.db")

    return str(Path(__file__).resolve().parents[1] / "data.db")


def _default_log_dir() -> str:
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).resolve().parent / "logs")

    return str(Path(__file__).resolve().parents[1] / "logs")


def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def _get_env_list(name: str, default: tuple[str, ...]) -> list[str]:
    value = os.getenv(name)
    if not value:
        return list(default)

    items = [item.strip() for item in value.split(",")]
    return [item for item in items if item]


@dataclass(frozen=True)
class Settings:
    app_title: str
    app_version: str
    host: str
    port: int
    log_level: str
    log_dir: str
    log_max_bytes: int
    log_backup_count: int
    cors_origins: list[str]
    db_path: str
    frontend_dist: str | None
    session_ttl_seconds: int
    admin_username: str
    admin_password: str
    edition: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_title=os.getenv("SC_APP_TITLE", "水泥配比计算 API"),
        app_version=os.getenv("SC_APP_VERSION", "1.0.0"),
        host=os.getenv("SC_HOST", "0.0.0.0"),
        port=_get_env_int("SC_PORT", 8000),
        log_level=os.getenv("SC_LOG_LEVEL", "INFO"),
        log_dir=os.getenv("SC_LOG_DIR", _default_log_dir()),
        log_max_bytes=_get_env_int("SC_LOG_MAX_BYTES", 5 * 1024 * 1024),
        log_backup_count=_get_env_int("SC_LOG_BACKUP_COUNT", 5),
        cors_origins=_get_env_list("SC_CORS_ORIGINS", DEFAULT_CORS_ORIGINS),
        db_path=os.getenv("SC_DB_PATH", _default_db_path()),
        frontend_dist=os.getenv("SC_FRONTEND_DIST") or None,
        session_ttl_seconds=_get_env_int("SC_SESSION_TTL_SECONDS", 24 * 60 * 60),
        admin_username=os.getenv("SC_ADMIN_USERNAME", "admin"),
        admin_password=os.getenv("SC_ADMIN_PASSWORD", "123456"),
        edition=(os.getenv("SC_EDITION", "web").strip().lower() or "web"),
    )