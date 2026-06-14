from __future__ import annotations

import contextvars
import json
import logging
import sys
import threading
from collections.abc import Mapping, Sequence
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


LOG_FORMAT = (
    "%(asctime)s %(levelname)s [%(name)s] "
    "[pid=%(process)d] [thread=%(threadName)s] [rid=%(request_id)s] %(message)s"
)
SENSITIVE_KEYS = {
    "password",
    "new_password",
    "old_password",
    "authorization",
    "access_token",
    "token",
    "secret",
}
REQUEST_ID = contextvars.ContextVar("request_id", default="-")


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = REQUEST_ID.get("-")
        return True


def bind_request_id(request_id: str) -> contextvars.Token[str]:
    return REQUEST_ID.set(request_id)


def reset_request_id(token: contextvars.Token[str]) -> None:
    REQUEST_ID.reset(token)


def _build_formatter() -> logging.Formatter:
    return logging.Formatter(LOG_FORMAT)


def _normalize_level(level: str) -> int:
    return getattr(logging, level.upper(), logging.INFO)


def _build_rotating_handler(path: Path, level: int, max_bytes: int, backup_count: int) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(_build_formatter())
    handler.addFilter(RequestContextFilter())
    return handler


def configure_logging(
    level: str,
    log_dir: str,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5,
) -> dict[str, str]:
    numeric_level = _normalize_level(level)
    log_directory = Path(log_dir).resolve()
    log_directory.mkdir(parents=True, exist_ok=True)

    app_log_path = log_directory / "app.log"
    error_log_path = log_directory / "error.log"

    formatter = _build_formatter()
    context_filter = RequestContextFilter()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(context_filter)

    app_handler = _build_rotating_handler(app_log_path, numeric_level, max_bytes, backup_count)
    error_handler = _build_rotating_handler(error_log_path, logging.ERROR, max_bytes, backup_count)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.filters.clear()
    root_logger.setLevel(numeric_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(app_handler)
    root_logger.addHandler(error_handler)

    logging.captureWarnings(True)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        named_logger = logging.getLogger(logger_name)
        named_logger.handlers.clear()
        named_logger.propagate = True
        named_logger.setLevel(numeric_level)

    return {
        "log_dir": str(log_directory),
        "app_log": str(app_log_path),
        "error_log": str(error_log_path),
    }


def install_global_exception_logging(logger: logging.Logger | None = None) -> None:
    target_logger = logger or logging.getLogger("wtcmd.runtime")

    def handle_exception(exc_type: type[BaseException], exc_value: BaseException, exc_traceback: Any) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        target_logger.critical(
            "Unhandled process exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = handle_exception

    def handle_thread_exception(args: threading.ExceptHookArgs) -> None:
        target_logger.critical(
            "Unhandled thread exception thread=%s",
            args.thread.name if args.thread else "unknown",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    threading.excepthook = handle_thread_exception


def sanitize_for_log(value: Any, *, max_string_length: int = 2000, max_items: int = 50) -> Any:
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = str(key)
            if normalized_key.lower() in SENSITIVE_KEYS:
                sanitized[normalized_key] = "***"
                continue
            sanitized[normalized_key] = sanitize_for_log(
                item,
                max_string_length=max_string_length,
                max_items=max_items,
            )
        return sanitized

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        limited = list(value[:max_items])
        sanitized_items = [
            sanitize_for_log(item, max_string_length=max_string_length, max_items=max_items)
            for item in limited
        ]
        if len(value) > max_items:
            sanitized_items.append(f"...({len(value) - max_items} more items)")
        return sanitized_items

    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")

    if isinstance(value, str):
        return value if len(value) <= max_string_length else f"{value[:max_string_length]}...(truncated)"

    if value is None or isinstance(value, (int, float, bool)):
        return value

    return repr(value)


def to_log_text(value: Any, *, default: str = "-", max_length: int = 4000) -> str:
    if value is None:
        return default

    sanitized = sanitize_for_log(value)
    if isinstance(sanitized, str):
        return sanitized if len(sanitized) <= max_length else f"{sanitized[:max_length]}...(truncated)"

    text = json.dumps(sanitized, ensure_ascii=False, default=str)
    return text if len(text) <= max_length else f"{text[:max_length]}...(truncated)"


def summarize_request_body(body: bytes, content_type: str | None) -> str:
    if not body:
        return "-"

    content_type_value = (content_type or "").lower()
    if "application/json" in content_type_value:
        try:
            parsed = json.loads(body.decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            return to_log_text(body.decode("utf-8", errors="replace"))
        return to_log_text(parsed)

    if "application/x-www-form-urlencoded" in content_type_value or "text/" in content_type_value:
        return to_log_text(body.decode("utf-8", errors="replace"))

    return f"<{content_type or 'binary'} {len(body)} bytes>"

