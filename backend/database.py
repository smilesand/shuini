"""
SQLite 数据库模块
================
表：
  users   - 用户账户（管理员/普通用户）
  records - 配比计算保存记录
"""
import sqlite3
import hashlib
import hmac
import json
import secrets
import time
from core.config import get_settings

settings = get_settings()
DB_PATH = settings.db_path


PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 600_000
SESSION_TTL_SECONDS = settings.session_ttl_seconds
DEFAULT_ADMIN_USERNAME = settings.admin_username
DEFAULT_ADMIN_PASSWORD = settings.admin_password

RECORD_JSON_FIELDS = {"trial_data", "design_data"}
RECORD_PAYLOAD_FIELDS = (
    "fcuk", "fb", "fcu0", "wb", "aa", "ab", "ac",
    "sand_ratio", "vg", "rhog", "rhos", "mg", "ms",
    "b1p", "rho1", "b2p", "rho2", "b3p", "rho3", "b4p", "rho4", "rhoc", "va",
    "rhob", "vp", "mb", "m1", "m2", "m3", "m4", "mc",
    "alpha", "mw", "ma", "total_mass", "trial_data", "design_data",
)
RECORD_METADATA_FIELDS = (
    "id", "name", "category", "created_by", "created_at", "project_id", "source",
)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _backfill_legacy_record_projects_conn(conn: sqlite3.Connection):
    project_rows = conn.execute(
        "SELECT id, created_by FROM projects ORDER BY id LIMIT 2"
    ).fetchall()
    if len(project_rows) != 1:
        return

    project = project_rows[0]
    orphan_count = conn.execute(
        "SELECT COUNT(*) FROM records WHERE project_id IS NULL"
    ).fetchone()[0]
    if orphan_count == 0:
        return

    owner_mismatch_count = conn.execute(
        "SELECT COUNT(*) FROM records WHERE project_id IS NULL AND created_by <> ?",
        (project["created_by"],),
    ).fetchone()[0]
    if owner_mismatch_count > 0:
        return

    conn.execute(
        "UPDATE records SET project_id=? WHERE project_id IS NULL",
        (project["id"],),
    )


def _table_has_column(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def _is_active_clause(alias: str = "") -> str:
    prefix = f"{alias}." if alias else ""
    return f"COALESCE({prefix}is_deleted, 0) = 0"


def _is_deleted_clause(alias: str = "") -> str:
    prefix = f"{alias}." if alias else ""
    return f"COALESCE({prefix}is_deleted, 0) = 1"


def _serialize_record_json(value: object | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _parse_record_json(value: object | None) -> object | None:
    if value is None or value == "":
        return None

    if isinstance(value, (dict, list)):
        return value

    try:
        return json.loads(str(value))
    except (TypeError, json.JSONDecodeError):
        return None


def _parse_record_payload(value: object | None) -> dict[str, object]:
    parsed = _parse_record_json(value)
    return parsed if isinstance(parsed, dict) else {}


def _build_record_payload_from_row(row: sqlite3.Row | None) -> dict[str, object]:
    if row is None:
        return {}

    row_keys = set(row.keys())
    payload: dict[str, object] = {}
    if "record_data" in row_keys:
        payload.update(_parse_record_payload(row["record_data"]))

    for field in RECORD_PAYLOAD_FIELDS:
        if field in payload or field not in row_keys:
            continue

        value = row[field]
        if field in RECORD_JSON_FIELDS:
            value = _parse_record_json(value)

        if value is not None:
            payload[field] = value

    return payload


def _merge_record_payload(existing_payload: dict[str, object], updates: dict) -> dict[str, object]:
    payload = dict(existing_payload)

    if "record_data" in updates:
        record_data_updates = updates.get("record_data")
        if record_data_updates is None:
            payload = {}
        else:
            parsed_updates = _parse_record_payload(record_data_updates)
            for key, value in parsed_updates.items():
                if value is None:
                    payload.pop(key, None)
                else:
                    payload[key] = value

    for field in RECORD_PAYLOAD_FIELDS:
        if field not in updates:
            continue

        value = updates.get(field)
        if field in RECORD_JSON_FIELDS:
            value = _parse_record_json(value) if isinstance(value, str) else value

        if value is None:
            payload.pop(field, None)
            continue

        payload[field] = value

    return payload


def _record_row_to_dict(row: sqlite3.Row) -> dict:
    payload = _build_record_payload_from_row(row)
    record = {field: row[field] for field in RECORD_METADATA_FIELDS if field in row.keys()}
    record["record_data"] = payload
    return record


def _backfill_legacy_record_payload_conn(conn: sqlite3.Connection):
    if not _table_has_column(conn, "records", "record_data"):
        return

    rows = conn.execute(
        "SELECT * FROM records WHERE record_data IS NULL OR record_data = ''"
    ).fetchall()
    for row in rows:
        payload = _build_record_payload_from_row(row)
        if not payload:
            continue
        conn.execute(
            "UPDATE records SET record_data=? WHERE id=?",
            (_serialize_record_json(payload), row["id"]),
        )


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            username     TEXT    NOT NULL UNIQUE,
            password     TEXT    NOT NULL,
            email        TEXT    NOT NULL DEFAULT '',
            phone        TEXT    NOT NULL DEFAULT '',
            is_admin     INTEGER NOT NULL DEFAULT 0,
            must_reset   INTEGER NOT NULL DEFAULT 1,
            created_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS records (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL,
            category     TEXT    NOT NULL DEFAULT 'hpc',
            created_by   TEXT    NOT NULL,
            created_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),

            project_id   INTEGER REFERENCES projects(id),
            record_data  TEXT,
            is_deleted   INTEGER NOT NULL DEFAULT 0,
            deleted_at   TEXT,
            deleted_by   TEXT,
            deleted_with_project INTEGER NOT NULL DEFAULT 0,
            source         TEXT    NOT NULL DEFAULT 'system'
        );
    """)
    # 创建默认管理员
    cur = conn.execute("SELECT password, must_reset FROM users WHERE username=?", (DEFAULT_ADMIN_USERNAME,))
    admin_row = cur.fetchone()
    if not admin_row:
        pw = _hash(DEFAULT_ADMIN_PASSWORD)
        conn.execute(
            "INSERT INTO users (username, password, is_admin, must_reset) VALUES (?,?,?,?)",
            (DEFAULT_ADMIN_USERNAME, pw, 1, 1),
        )
    else:
        if verify_password(DEFAULT_ADMIN_PASSWORD, admin_row["password"]):
            conn.execute(
                "UPDATE users SET password=?, must_reset=1 WHERE username=?",
                (_hash(DEFAULT_ADMIN_PASSWORD), DEFAULT_ADMIN_USERNAME),
            )
    # 迁移：添加 category 列
    try:
        conn.execute("ALTER TABLE records ADD COLUMN category TEXT NOT NULL DEFAULT 'hpc'")
    except sqlite3.OperationalError:
        pass
    # 迁移：添加 email / phone 列
    for col in ("email", "phone"):
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass

    # 迁移：projects 表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            project_code TEXT    NOT NULL,
            project_name TEXT    NOT NULL,
            requirements TEXT    NOT NULL DEFAULT '',
            created_by   TEXT    NOT NULL,
            created_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            is_deleted   INTEGER NOT NULL DEFAULT 0,
            deleted_at   TEXT,
            deleted_by   TEXT,
            source       TEXT    NOT NULL DEFAULT 'system'
        )
    """)

    # 迁移：records 表添加 project_id
    try:
        conn.execute("ALTER TABLE records ADD COLUMN project_id INTEGER REFERENCES projects(id)")
    except sqlite3.OperationalError:
        pass

    # 迁移：records 表添加统一 JSON 载荷
    try:
        conn.execute("ALTER TABLE records ADD COLUMN record_data TEXT")
    except sqlite3.OperationalError:
        pass

    for ddl in (
        "ALTER TABLE records ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE records ADD COLUMN deleted_at TEXT",
        "ALTER TABLE records ADD COLUMN deleted_by TEXT",
        "ALTER TABLE records ADD COLUMN deleted_with_project INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE projects ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE projects ADD COLUMN deleted_at TEXT",
        "ALTER TABLE projects ADD COLUMN deleted_by TEXT",
        "ALTER TABLE projects ADD COLUMN source TEXT NOT NULL DEFAULT 'system'",
        "ALTER TABLE records ADD COLUMN source TEXT NOT NULL DEFAULT 'system'",
    ):
        try:
            conn.execute(ddl)
        except sqlite3.OperationalError:
            pass

    # 服务端会话表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            token_hash   TEXT    NOT NULL UNIQUE,
            username     TEXT    NOT NULL REFERENCES users(username) ON DELETE CASCADE,
            expires_at   INTEGER NOT NULL,
            created_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_username ON sessions(username)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_records_created_by ON records(created_by)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_records_project_id ON records(project_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_records_category ON records(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_records_is_deleted ON records(is_deleted)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_is_deleted ON projects(is_deleted)")
    conn.execute("DROP INDEX IF EXISTS idx_projects_project_code")
    try:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_owner_code_active "
            "ON projects(created_by, project_code) WHERE is_deleted = 0"
        )
    except sqlite3.IntegrityError:
        pass

    _backfill_legacy_record_payload_conn(conn)
    _backfill_legacy_record_projects_conn(conn)

    _cleanup_expired_sessions_conn(conn)

    conn.commit()
    conn.close()


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


def is_admin_user(username: str) -> bool:
    user = get_user(username)
    return bool(user and user["is_admin"])


def get_user(username: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_user(username: str, password: str, is_admin: bool = False,
                email: str = "", phone: str = "") -> dict:
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
    """更新用户个人资料（邮箱、手机号）"""
    conn = get_db()
    fields = []
    values = []
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


# ── 记录 ──

def _ensure_project_access_conn(
    conn: sqlite3.Connection,
    project_id: int,
    username: str,
    is_admin: bool,
    *,
    deleted_only: bool = False,
) -> bool:
    params: list[object] = [project_id]
    sql = "SELECT id FROM projects WHERE id=?"
    sql += f" AND {_is_deleted_clause() if deleted_only else _is_active_clause()}"
    if not is_admin:
        sql += " AND created_by=?"
        params.append(username)
    return conn.execute(sql, params).fetchone() is not None


def _ensure_unique_project_code_conn(
    conn: sqlite3.Connection,
    project_code: str,
    created_by: str,
    exclude_project_id: int | None = None,
):
    params: list[object] = [created_by, project_code]
    sql = f"SELECT id FROM projects WHERE created_by=? AND project_code=? AND {_is_active_clause()}"
    if exclude_project_id is not None:
        sql += " AND id<>?"
        params.append(exclude_project_id)
    if conn.execute(sql, params).fetchone():
        raise RuntimeError(f"项目编号 '{project_code}' 已存在")


def _ensure_record_access_conn(
    conn: sqlite3.Connection,
    record_id: int,
    username: str,
    is_admin: bool,
    *,
    deleted_only: bool = False,
) -> bool:
    params: list[object] = [record_id]
    sql = "SELECT id FROM records WHERE id=?"
    sql += f" AND {_is_deleted_clause() if deleted_only else _is_active_clause()}"
    if not is_admin:
        sql += " AND created_by=?"
        params.append(username)
    return conn.execute(sql, params).fetchone() is not None


def get_record(record_id: int, *, username: str, is_admin: bool = False) -> dict | None:
    """获取单条记录（含权限检查）。"""
    conn = get_db()
    params: list[object] = [record_id]
    sql = f"SELECT * FROM records WHERE id=? AND {_is_active_clause()}"
    if not is_admin:
        sql += " AND created_by=?"
        params.append(username)
    row = conn.execute(sql, params).fetchone()
    conn.close()
    if row is None:
        return None
    return _record_row_to_dict(row)


def save_record(data: dict, *, username: str, is_admin: bool = False) -> int:
    conn = get_db()
    record_id = data.get("id")
    record_id_int: int | None = None
    if record_id is not None:
        record_id_int = int(record_id)

    project_id = data.get("project_id")
    project_id_int: int | None = None
    if project_id is not None:
        project_id_int = int(project_id)

    if record_id_int is not None and not _ensure_record_access_conn(conn, record_id_int, username, is_admin):
        conn.close()
        raise RuntimeError(f"记录 #{record_id_int} 不存在或无权限修改")

    if "project_id" in data and project_id_int is not None and not _ensure_project_access_conn(conn, project_id_int, username, is_admin):
        conn.close()
        raise RuntimeError("项目不存在或无权限关联记录")

    existing_row: sqlite3.Row | None = None
    if record_id_int is not None:
        existing_row = conn.execute(
            f"SELECT * FROM records WHERE id=? AND {_is_active_clause()}",
            (record_id_int,),
        ).fetchone()

    existing_payload = _build_record_payload_from_row(existing_row)
    merged_payload = _merge_record_payload(existing_payload, data)
    record_data = _serialize_record_json(merged_payload)

    if existing_row is not None:
        name = data.get("name", existing_row["name"])
        category = data.get("category", existing_row["category"])
        final_project_id = project_id_int if "project_id" in data else existing_row["project_id"]
        final_source = data.get("source", existing_row["source"] if "source" in existing_row.keys() else "system")
    else:
        name = data.get("name")
        category = data.get("category", "hpc")
        final_project_id = project_id_int
        final_source = data.get("source", "system")

    if not name:
        conn.close()
        raise RuntimeError("记录名称不能为空")

    try:
        if record_id_int is not None:
            conn.execute(
                "UPDATE records SET name=?, category=?, project_id=?, record_data=?, source=?, deleted_with_project=0 WHERE id=?",
                [name, category, final_project_id, record_data, final_source, record_id_int],
            )
            conn.commit()
            conn.close()
            return record_id_int

        cur = conn.execute(
            "INSERT INTO records (name, category, created_by, project_id, record_data, source) VALUES (?,?,?,?,?,?)",
            [name, category, username, final_project_id, record_data, final_source],
        )
        conn.commit()
    except sqlite3.Error as e:
        conn.close()
        raise RuntimeError(f"保存记录失败: {e}")
    rid = cur.lastrowid
    conn.close()
    if rid is None:
        raise RuntimeError("保存记录失败：无法获取插入 ID")
    return rid


def list_records(category: str | None = None, search: str = "",
                 page: int = 1, page_size: int = 20,
                 project_id: int | None = None,
                 *, username: str | None = None, is_admin: bool = False) -> dict:
    """分页查询记录，支持按名称/创建人搜索"""
    conn = get_db()
    params: list = []
    where_clauses: list[str] = [_is_active_clause()]

    if username and not is_admin:
        where_clauses.append("created_by = ?")
        params.append(username)

    if project_id is not None:
        where_clauses.append("project_id = ?")
        params.append(project_id)

    if category:
        where_clauses.append("category = ?")
        params.append(category)

    if search:
        where_clauses.append("(name LIKE ? OR created_by LIKE ?)")
        kw = f"%{search}%"
        params.extend([kw, kw])

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    # 总数
    count_row = conn.execute(
        f"SELECT COUNT(*) FROM records {where_sql}", params
    ).fetchone()
    total = count_row[0] if count_row else 0

    # 分页
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT * FROM records {where_sql} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [page_size, offset],
    ).fetchall()
    conn.close()

    return {
        "items": [_record_row_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def delete_record(record_id: int, username: str | None = None, is_admin: bool = False):
    conn = get_db()
    params: list[object] = [record_id]
    sql = f"SELECT id FROM records WHERE id=? AND {_is_active_clause()}"
    if username and not is_admin:
        sql += " AND created_by=?"
        params.append(username)
    cur = conn.execute(sql, params)
    if not cur.fetchone():
        conn.close()
        raise RuntimeError(f"记录 #{record_id} 不存在或无权限删除")
    conn.execute(
        "UPDATE records SET is_deleted=1, deleted_at=datetime('now','localtime'), deleted_by=?, deleted_with_project=0 WHERE id=?",
        (username or "", record_id),
    )
    conn.commit()
    conn.close()


# ── 项目 ──

def create_project(project_code: str, project_name: str, created_by: str,
                   requirements: str = "", source: str = "system") -> dict:
    conn = get_db()
    _ensure_unique_project_code_conn(conn, project_code, created_by)
    try:
        cur = conn.execute(
            "INSERT INTO projects (project_code, project_name, requirements, created_by, source) VALUES (?,?,?,?,?)",
            (project_code, project_name, requirements, created_by, source),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise RuntimeError(f"项目编号 '{project_code}' 已存在")
    row = conn.execute("SELECT * FROM projects WHERE id=?", (cur.lastrowid,)).fetchone()
    conn.close()
    if row is None:
        raise RuntimeError("创建项目失败")
    return dict(row)


def list_projects(search: str = "", page: int = 1, page_size: int = 20,
                  *, username: str | None = None, is_admin: bool = False) -> dict:
    conn = get_db()
    params: list = []
    where_clauses: list[str] = [_is_active_clause("p")]
    record_count_filter = f" AND {_is_active_clause()}"
    if username and not is_admin:
        record_count_filter += " AND created_by = p.created_by"

    if username and not is_admin:
        where_clauses.append("p.created_by = ?")
        params.append(username)

    if search:
        kw = f"%{search}%"
        where_clauses.append("(p.project_code LIKE ? OR p.project_name LIKE ?)")
        params.extend([kw, kw])

    where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    total = conn.execute(f"SELECT COUNT(*) FROM projects p {where}", params).fetchone()[0]
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT p.*, (SELECT COUNT(*) FROM records WHERE project_id=p.id{record_count_filter}) AS record_count "
        f"FROM projects p {where} ORDER BY p.id DESC LIMIT ? OFFSET ?",
        params + [page_size, offset],
    ).fetchall()
    conn.close()
    return {"items": [dict(r) for r in rows], "total": total, "page": page, "page_size": page_size}


def get_project(project_id: int, *, username: str | None = None, is_admin: bool = False) -> dict | None:
    conn = get_db()
    params: list[object] = [project_id]
    where = f"p.id=? AND {_is_active_clause('p')}"
    record_count_filter = f" AND {_is_active_clause()}"
    if username and not is_admin:
        where += " AND p.created_by=?"
        params.append(username)
        record_count_filter += " AND created_by = p.created_by"
    row = conn.execute(
        f"SELECT p.*, (SELECT COUNT(*) FROM records WHERE project_id=p.id{record_count_filter}) AS record_count "
        f"FROM projects p WHERE {where}", params
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_project(project_id: int, project_code: str | None = None,
                   project_name: str | None = None, requirements: str | None = None,
                   *, username: str, is_admin: bool = False):
    conn = get_db()
    if not _ensure_project_access_conn(conn, project_id, username, is_admin):
        conn.close()
        raise RuntimeError(f"项目 #{project_id} 不存在或无权限修改")

    project_row = conn.execute(
        f"SELECT created_by FROM projects WHERE id=? AND {_is_active_clause()}",
        (project_id,),
    ).fetchone()
    if project_row is None:
        conn.close()
        raise RuntimeError(f"项目 #{project_id} 不存在或无权限修改")

    fields = []
    vals = []
    if project_code is not None:
        _ensure_unique_project_code_conn(
            conn,
            project_code,
            project_row["created_by"],
            exclude_project_id=project_id,
        )
        fields.append("project_code=?")
        vals.append(project_code)
    if project_name is not None:
        fields.append("project_name=?")
        vals.append(project_name)
    if requirements is not None:
        fields.append("requirements=?")
        vals.append(requirements)
    if not fields:
        conn.close()
        return
    fields.append("updated_at=datetime('now','localtime')")
    vals.append(project_id)
    conn.execute(f"UPDATE projects SET {','.join(fields)} WHERE id=?", vals)
    conn.commit()
    conn.close()


def delete_project(project_id: int, *, username: str | None = None, is_admin: bool = False):
    conn = get_db()
    if not _ensure_project_access_conn(conn, project_id, username or "", is_admin):
        conn.close()
        raise RuntimeError(f"项目 #{project_id} 不存在或无权限删除")
    conn.execute(
        "UPDATE projects SET is_deleted=1, deleted_at=datetime('now','localtime'), deleted_by=?, updated_at=datetime('now','localtime') WHERE id=?",
        (username or "", project_id),
    )
    conn.execute(
        "UPDATE records "
        "SET is_deleted=1, "
        "    deleted_at=CASE WHEN COALESCE(is_deleted, 0)=0 THEN datetime('now','localtime') ELSE deleted_at END, "
        "    deleted_by=CASE WHEN COALESCE(is_deleted, 0)=0 THEN ? ELSE deleted_by END, "
        "    deleted_with_project=CASE WHEN COALESCE(is_deleted, 0)=0 THEN 1 ELSE deleted_with_project END "
        "WHERE project_id=?",
        (username or "", project_id),
    )
    conn.commit()
    conn.close()


def list_project_records(project_id: int, *, username: str, is_admin: bool = False) -> list[dict]:
    conn = get_db()
    if not _ensure_project_access_conn(conn, project_id, username, is_admin):
        conn.close()
        raise RuntimeError(f"项目 #{project_id} 不存在或无权限访问")
    params: list[object] = [project_id]
    sql = f"SELECT * FROM records WHERE project_id=? AND {_is_active_clause()}"
    if not is_admin:
        sql += " AND created_by=?"
        params.append(username)
    sql += " ORDER BY id DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [_record_row_to_dict(r) for r in rows]


def list_recycle_bin(
    *,
    item_type: str = "all",
    search: str = "",
    page: int = 1,
    page_size: int = 20,
    username: str | None = None,
    is_admin: bool = False,
) -> dict:
    if item_type not in {"all", "project", "record"}:
        raise RuntimeError("无效的回收站数据类型")

    conn = get_db()
    search_kw = f"%{search}%"
    subqueries: list[str] = []
    params: list[object] = []

    if item_type in {"all", "project"}:
        project_where = [_is_deleted_clause("p")]
        if username and not is_admin:
            project_where.append("p.created_by = ?")
            params.append(username)
        if search:
            project_where.append("(p.project_code LIKE ? OR p.project_name LIKE ? OR p.created_by LIKE ?)")
            params.extend([search_kw, search_kw, search_kw])
        subqueries.append(
            "SELECT 'project' AS item_type, "
            "       p.id AS id, "
            "       p.project_name AS name, "
            "       NULL AS category, "
            "       p.project_code AS project_code, "
            "       p.project_name AS project_name, "
            "       NULL AS project_id, "
            "       p.created_by AS created_by, "
            "       p.created_at AS created_at, "
            "       p.deleted_at AS deleted_at, "
            "       p.deleted_by AS deleted_by, "
            "       0 AS deleted_with_project "
            f"FROM projects p WHERE {' AND '.join(project_where)}"
        )

    if item_type in {"all", "record"}:
        record_where = [_is_deleted_clause("r")]
        if username and not is_admin:
            record_where.append("r.created_by = ?")
            params.append(username)
        if search:
            record_where.append(
                "(r.name LIKE ? OR r.created_by LIKE ? OR COALESCE(p.project_code, '') LIKE ? OR COALESCE(p.project_name, '') LIKE ?)"
            )
            params.extend([search_kw, search_kw, search_kw, search_kw])
        subqueries.append(
            "SELECT 'record' AS item_type, "
            "       r.id AS id, "
            "       r.name AS name, "
            "       r.category AS category, "
            "       COALESCE(p.project_code, '') AS project_code, "
            "       COALESCE(p.project_name, '') AS project_name, "
            "       r.project_id AS project_id, "
            "       r.created_by AS created_by, "
            "       r.created_at AS created_at, "
            "       r.deleted_at AS deleted_at, "
            "       r.deleted_by AS deleted_by, "
            "       COALESCE(r.deleted_with_project, 0) AS deleted_with_project "
            "FROM records r "
            "LEFT JOIN projects p ON p.id = r.project_id "
            f"WHERE {' AND '.join(record_where)}"
        )

    union_sql = " UNION ALL ".join(subqueries)
    total = conn.execute(
        f"SELECT COUNT(*) FROM ({union_sql}) AS recycle_items",
        params,
    ).fetchone()[0]
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT * FROM ({union_sql}) AS recycle_items "
        "ORDER BY deleted_at DESC, item_type ASC, id DESC LIMIT ? OFFSET ?",
        params + [page_size, offset],
    ).fetchall()
    conn.close()
    return {
        "items": [dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def restore_record(record_id: int, *, username: str | None = None, is_admin: bool = False):
    conn = get_db()
    if not _ensure_record_access_conn(conn, record_id, username or "", is_admin, deleted_only=True):
        conn.close()
        raise RuntimeError(f"记录 #{record_id} 不存在或无权限恢复")

    row = conn.execute("SELECT project_id FROM records WHERE id=?", (record_id,)).fetchone()
    if row is None:
        conn.close()
        raise RuntimeError(f"记录 #{record_id} 不存在或无权限恢复")

    project_id = row["project_id"]
    if project_id is not None and _ensure_project_access_conn(
        conn,
        int(project_id),
        username or "",
        is_admin,
        deleted_only=True,
    ):
        conn.execute(
            "UPDATE projects SET is_deleted=0, deleted_at=NULL, deleted_by=NULL, updated_at=datetime('now','localtime') WHERE id=?",
            (project_id,),
        )

    conn.execute(
        "UPDATE records SET is_deleted=0, deleted_at=NULL, deleted_by=NULL, deleted_with_project=0 WHERE id=?",
        (record_id,),
    )
    conn.commit()
    conn.close()


def purge_record(record_id: int, *, username: str | None = None, is_admin: bool = False):
    conn = get_db()
    if not _ensure_record_access_conn(conn, record_id, username or "", is_admin, deleted_only=True):
        conn.close()
        raise RuntimeError(f"记录 #{record_id} 不存在或无权限彻底删除")
    conn.execute("DELETE FROM records WHERE id=?", (record_id,))
    conn.commit()
    conn.close()


def restore_project(project_id: int, *, username: str | None = None, is_admin: bool = False):
    conn = get_db()
    if not _ensure_project_access_conn(conn, project_id, username or "", is_admin, deleted_only=True):
        conn.close()
        raise RuntimeError(f"项目 #{project_id} 不存在或无权限恢复")
    conn.execute(
        "UPDATE projects SET is_deleted=0, deleted_at=NULL, deleted_by=NULL, updated_at=datetime('now','localtime') WHERE id=?",
        (project_id,),
    )
    conn.execute(
        "UPDATE records SET is_deleted=0, deleted_at=NULL, deleted_by=NULL, deleted_with_project=0 "
        "WHERE project_id=? AND COALESCE(deleted_with_project, 0)=1 AND COALESCE(is_deleted, 0)=1",
        (project_id,),
    )
    conn.commit()
    conn.close()


def purge_project(project_id: int, *, username: str | None = None, is_admin: bool = False):
    conn = get_db()
    if not _ensure_project_access_conn(conn, project_id, username or "", is_admin, deleted_only=True):
        conn.close()
        raise RuntimeError(f"项目 #{project_id} 不存在或无权限彻底删除")
    conn.execute("DELETE FROM records WHERE project_id=?", (project_id,))
    conn.execute("DELETE FROM projects WHERE id=?", (project_id,))
    conn.commit()
    conn.close()
