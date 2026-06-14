from __future__ import annotations

import hashlib
import secrets
import sqlite3
import time

from core.config import get_settings
from core.db import get_db


SESSION_TTL_SECONDS = get_settings().session_ttl_seconds


def _hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _cleanup_expired_sessions_conn(conn: sqlite3.Connection, now: int | None = None):
    conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now or int(time.time()),))


def _revoke_all_sessions_conn(conn: sqlite3.Connection, username: str):
    conn.execute("DELETE FROM sessions WHERE username=?", (username,))


def _revoke_session_conn(conn: sqlite3.Connection, token: str):
    conn.execute("DELETE FROM sessions WHERE token_hash=?", (_hash_session_token(token),))


def create_session(username: str, ttl_seconds: int = SESSION_TTL_SECONDS) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + ttl_seconds
    conn = get_db()
    _cleanup_expired_sessions_conn(conn)
    conn.execute(
        "INSERT INTO sessions (token_hash, username, expires_at) VALUES (?,?,?)",
        (_hash_session_token(token), username, expires_at),
    )
    conn.commit()
    conn.close()
    return token


def get_session_user(token: str) -> str | None:
    if not token:
        return None

    now = int(time.time())
    conn = get_db()
    _cleanup_expired_sessions_conn(conn, now)
    row = conn.execute(
        "SELECT username FROM sessions WHERE token_hash=? AND expires_at>?",
        (_hash_session_token(token), now),
    ).fetchone()
    conn.commit()
    conn.close()
    return row["username"] if row else None


def revoke_all_sessions(username: str):
    conn = get_db()
    _revoke_all_sessions_conn(conn, username)
    conn.commit()
    conn.close()


def revoke_session(token: str):
    if not token:
        return

    conn = get_db()
    _revoke_session_conn(conn, token)
    conn.commit()
    conn.close()