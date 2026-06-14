from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3

from core.db import get_db
from repositories.sessions import _revoke_all_sessions_conn


PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 600_000


def _legacy_hash(password: str) -> str:
    return hashlib.sha256(f"shuini_salt_{password}".encode()).hexdigest()


def _hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return f"{PASSWORD_SCHEME}${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def password_needs_rehash(hashed: str) -> bool:
    if not hashed.startswith(f"{PASSWORD_SCHEME}$"):
        return True

    parts = hashed.split("$", 3)
    if len(parts) != 4:
        return True

    try:
        return int(parts[1]) < PASSWORD_ITERATIONS
    except ValueError:
        return True


def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False

    if hashed.startswith(f"{PASSWORD_SCHEME}$"):
        parts = hashed.split("$", 3)
        if len(parts) != 4:
            return False
        _, iterations_text, salt_hex, digest_hex = parts
        try:
            iterations = int(iterations_text)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(digest_hex)
        except ValueError:
            return False

        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(actual, expected)

    return hmac.compare_digest(_legacy_hash(password), hashed)


def upgrade_password_hash(username: str, password: str):
    conn = get_db()
    cur = conn.execute(
        "UPDATE users SET password=? WHERE username=?",
        (_hash(password), username),
    )
    if cur.rowcount == 0:
        conn.close()
        raise RuntimeError(f"用户 '{username}' 不存在")
    conn.commit()
    conn.close()


def get_user(username: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def is_admin_user(username: str) -> bool:
    user = get_user(username)
    return bool(user and user["is_admin"])


def create_user(
    username: str,
    password: str,
    is_admin: bool = False,
    email: str = "",
    phone: str = "",
) -> dict:
    conn = get_db()
    pw = _hash(password)
    try:
        cur = conn.execute(
            "INSERT INTO users (username, password, is_admin, email, phone) VALUES (?,?,?,?,?)",
            (username, pw, int(is_admin), email, phone),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise RuntimeError(f"用户名 '{username}' 已存在")
    row = conn.execute(
        "SELECT id, username, email, phone, is_admin, must_reset, created_at FROM users WHERE id=?",
        (cur.lastrowid,),
    ).fetchone()
    conn.close()
    if row is None:
        raise RuntimeError("创建用户失败：无法读取新建用户")
    return dict(row)


def update_password(
    username: str,
    new_password: str,
    *,
    must_reset: bool = False,
    revoke_existing_sessions: bool = True,
):
    conn = get_db()
    pw = _hash(new_password)
    cur = conn.execute(
        "UPDATE users SET password=?, must_reset=? WHERE username=?",
        (pw, int(must_reset), username),
    )
    if cur.rowcount == 0:
        conn.close()
        raise RuntimeError(f"用户 '{username}' 不存在")
    if revoke_existing_sessions:
        _revoke_all_sessions_conn(conn, username)
    conn.commit()
    conn.close()


def list_users() -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT id, username, email, phone, is_admin, must_reset, created_at FROM users ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_user(username: str):
    conn = get_db()
    cur = conn.execute("SELECT id FROM users WHERE username=? AND is_admin=0", (username,))
    if not cur.fetchone():
        conn.close()
        raise RuntimeError(f"用户 '{username}' 不存在或为管理员，无法删除")
    conn.execute("DELETE FROM users WHERE username=? AND is_admin=0", (username,))
    conn.commit()
    conn.close()


def update_profile(username: str, email: str | None = None, phone: str | None = None):
    conn = get_db()
    fields: list[str] = []
    values: list[object] = []
    if email is not None:
        fields.append("email=?")
        values.append(email)
    if phone is not None:
        fields.append("phone=?")
        values.append(phone)
    if not fields:
        conn.close()
        return
    values.append(username)
    conn.execute(f"UPDATE users SET {','.join(fields)} WHERE username=?", values)
    conn.commit()
    conn.close()