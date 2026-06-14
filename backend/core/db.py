from __future__ import annotations

import sqlite3


def _current_db_path() -> str:
    import database

    return database.DB_PATH


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_current_db_path())
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


def init_db():
    import database

    database.init_db()