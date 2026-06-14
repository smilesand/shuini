from __future__ import annotations

import sqlite3

from core.db import get_db


def _ensure_project_access_conn(
    conn: sqlite3.Connection,
    project_id: int,
    username: str,
    is_admin: bool,
) -> bool:
    params: list[object] = [project_id]
    sql = "SELECT id FROM projects WHERE id=?"
    if not is_admin:
        sql += " AND created_by=?"
        params.append(username)
    return conn.execute(sql, params).fetchone() is not None


def _ensure_unique_project_code_conn(
    conn: sqlite3.Connection,
    project_code: str,
    exclude_project_id: int | None = None,
):
    params: list[object] = [project_code]
    sql = "SELECT id FROM projects WHERE project_code=?"
    if exclude_project_id is not None:
        sql += " AND id<>?"
        params.append(exclude_project_id)
    if conn.execute(sql, params).fetchone():
        raise RuntimeError(f"项目编号 '{project_code}' 已存在")


def create_project(project_code: str, project_name: str, created_by: str, requirements: str = "") -> dict:
    conn = get_db()
    _ensure_unique_project_code_conn(conn, project_code)
    try:
        cur = conn.execute(
            "INSERT INTO projects (project_code, project_name, requirements, created_by) VALUES (?,?,?,?)",
            (project_code, project_name, requirements, created_by),
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


def list_projects(
    search: str = "",
    page: int = 1,
    page_size: int = 20,
    *,
    username: str | None = None,
    is_admin: bool = False,
) -> dict:
    conn = get_db()
    params: list[object] = []
    where_clauses: list[str] = []

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
        f"SELECT p.*, (SELECT COUNT(*) FROM records WHERE project_id=p.id) AS record_count "
        f"FROM projects p {where} ORDER BY p.id DESC LIMIT ? OFFSET ?",
        params + [page_size, offset],
    ).fetchall()
    conn.close()
    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_project(
    project_id: int,
    *,
    username: str | None = None,
    is_admin: bool = False,
) -> dict | None:
    conn = get_db()
    params: list[object] = [project_id]
    where = "p.id=?"
    if username and not is_admin:
        where += " AND p.created_by=?"
        params.append(username)
    row = conn.execute(
        "SELECT p.*, (SELECT COUNT(*) FROM records WHERE project_id=p.id) AS record_count "
        f"FROM projects p WHERE {where}",
        params,
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_project(
    project_id: int,
    project_code: str | None = None,
    project_name: str | None = None,
    requirements: str | None = None,
    *,
    username: str,
    is_admin: bool = False,
):
    conn = get_db()
    if not _ensure_project_access_conn(conn, project_id, username, is_admin):
        conn.close()
        raise RuntimeError(f"项目 #{project_id} 不存在或无权限修改")

    fields: list[str] = []
    vals: list[object] = []
    if project_code is not None:
        _ensure_unique_project_code_conn(conn, project_code, exclude_project_id=project_id)
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
    conn.execute("UPDATE records SET project_id=NULL WHERE project_id=?", (project_id,))
    conn.execute("DELETE FROM projects WHERE id=?", (project_id,))
    conn.commit()
    conn.close()