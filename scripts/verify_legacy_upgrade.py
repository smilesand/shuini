"""旧版数据库平滑升级验证脚本
================================
目的：证明老客户端（**旧版明文 SQLite**，可能是 WAL 日志模式、且 schema 缺少新列）
升级到当前整库加密版本后：

  1. 旧库里的业务数据（用户 / 项目 / 配比记录）会被**完整读入**新版数据库；
  2. 缺失的新列会被自动补齐（ALTER TABLE 迁移）；
  3. 首次提交后磁盘文件被**整库加密**覆盖（``WTSCDB01`` 头），旧明文不再残留；
  4. 旁路文件 ``-wal`` / ``-shm`` 会被清理；
  5. 模拟“重启客户端”后仍能从加密库读回全部数据 —— 升级对用户**无感知、零丢失**。

本脚本只在**临时目录**里操作，绝不触碰真实客户端数据库。

用法（仓库根目录运行）::

    python scripts/verify_legacy_upgrade.py

退出码 0 = 全部校验通过；非 0 = 有校验失败。
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"

# 旧版（明文）客户端的精简 schema：故意省略后续版本才加入的列
# （users 无 email/phone；records 无 project_id/record_data/source/软删除列；无 projects/sessions 表），
# 以此同时验证“数据保留”和“ALTER TABLE 自动补列”两条迁移路径。
LEGACY_SCHEMA = """
CREATE TABLE users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT NOT NULL UNIQUE,
    password   TEXT NOT NULL,
    is_admin   INTEGER NOT NULL DEFAULT 0,
    must_reset INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE TABLE records (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
"""


def _make_legacy_db(db_path: Path) -> dict:
    """生成一个旧版明文 + WAL 模式的数据库，并塞入可校验的样本数据。"""
    conn = sqlite3.connect(db_path)
    try:
        # 旧客户端常见为 WAL 日志模式——这是迁移最容易踩坑的情形。
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(LEGACY_SCHEMA)
        conn.execute(
            "INSERT INTO users (username, password, is_admin, must_reset) VALUES (?,?,?,?)",
            ("legacy_user", "pbkdf2_sha256$1$00$dead", 0, 0),
        )
        records = [
            ("旧记录-甲", "legacy_user"),
            ("旧记录-乙", "legacy_user"),
            ("旧记录-丙", "admin"),
        ]
        conn.executemany(
            "INSERT INTO records (name, created_by) VALUES (?,?)", records
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "user_count": 1,
        "record_names": {"旧记录-甲", "旧记录-乙", "旧记录-丙"},
    }


def _read_head(path: Path, n: int = 16) -> bytes:
    with open(path, "rb") as f:
        return f.read(n)


def main() -> int:
    ok = True

    def check(label: str, condition: bool) -> None:
        nonlocal ok
        status = "PASS" if condition else "FAIL"
        if not condition:
            ok = False
        print(f"  [{status}] {label}")

    tmp_root = Path(tempfile.mkdtemp(prefix="wt_legacy_upgrade_"))
    db_path = tmp_root / "data.db"

    # 必须在 import 后端模块之前设置环境变量：database.py 在导入时读取 DB_PATH。
    os.environ["SC_DB_PATH"] = str(db_path)
    os.environ["SC_EDITION"] = "desktop"  # 桌面版才启用整库加密
    sys.path.insert(0, str(BACKEND_DIR))

    print(f"[*] 临时工作目录：{tmp_root}")
    print("[*] 步骤 1：构造旧版明文(WAL) 数据库并写入样本数据 …")
    expected = _make_legacy_db(db_path)

    # 确认初始确实是明文 SQLite，且数据库以 WAL 日志模式持久化
    print("[*] 步骤 2：校验初始状态为旧版明文库 …")
    head16 = _read_head(db_path)
    check("初始文件是明文 SQLite（SQLite format 3）",
          head16 == b"SQLite format 3\x00")
    # WAL 模式是持久属性，写入 SQLite 文件头第 18/19 字节（=2 表示 WAL）。
    # 干净关闭最后一个连接时 -wal/-shm 旁路文件会被检查点合并并删除，
    # 但文件头的 WAL 标记仍然保留——这正是迁移序列化时会踩坑的情形。
    header20 = _read_head(db_path, 20)
    check("初始数据库以 WAL 日志模式持久化（文件头标记=2）",
          header20[18] == 2 and header20[19] == 2)

    print("[*] 步骤 3：以新版后端启动逻辑打开并初始化（触发迁移 + 首次加密落盘）…")
    from core import secure_db  # noqa: E402
    import database  # noqa: E402

    # 走完整初始化：读入旧库 -> 建表/补列 -> commit -> 整库加密覆盖磁盘
    database.init_db()

    print("[*] 步骤 4：校验磁盘已变为整库加密格式、旁路文件已清理 …")
    head = _read_head(db_path)
    check("磁盘文件头部已是加密魔数 WTSCDB01", secure_db.is_encrypted_blob(head))
    check("磁盘文件已不再是明文 SQLite", head != b"SQLite format 3\x00")
    check("-wal 旁路文件已被清理",
          not (db_path.parent / (db_path.name + "-wal")).exists())
    check("-shm 旁路文件已被清理",
          not (db_path.parent / (db_path.name + "-shm")).exists())

    print("[*] 步骤 5：校验旧数据完整保留 + 新列已自动补齐 …")
    conn = database.get_db()
    rec_rows = conn.execute("SELECT name FROM records ORDER BY id").fetchall()
    got_names = {r["name"] for r in rec_rows}
    check("旧配比记录条数一致（3 条）", len(rec_rows) == 3)
    check("旧配比记录内容完整保留", got_names == expected["record_names"])

    legacy_user = conn.execute(
        "SELECT username, email, phone FROM users WHERE username=?", ("legacy_user",)
    ).fetchone()
    check("旧用户仍然存在", legacy_user is not None)
    check("迁移自动补齐了 users.email / users.phone 列",
          legacy_user is not None and legacy_user["email"] == "" and legacy_user["phone"] == "")

    # 新列：records.project_id / source / is_deleted 应已存在且有默认值
    rec_cols = {row[1] for row in conn.execute("PRAGMA table_info(records)").fetchall()}
    for col in ("project_id", "record_data", "source", "is_deleted", "deleted_at"):
        check(f"迁移自动补齐了 records.{col} 列", col in rec_cols)

    # 新建的表：projects / sessions 应存在
    tables = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    check("新增 projects 表已创建", "projects" in tables)
    check("新增 sessions 表已创建", "sessions" in tables)

    print("[*] 步骤 6：模拟客户端重启（丢弃内存连接，重新从加密库读回）…")
    # 重置共享内存连接，强制下次 get_db() 从（现已加密的）磁盘文件重新解密装载。
    database._shared_conn = None
    database._shared_conn_path = None
    conn2 = database.get_db()
    rec_rows2 = conn2.execute("SELECT name FROM records ORDER BY id").fetchall()
    got_names2 = {r["name"] for r in rec_rows2}
    check("重启后仍能从加密库读回全部旧记录", got_names2 == expected["record_names"])

    # 清理临时目录
    try:
        database._shared_conn = None
        database._shared_conn_path = None
        import shutil

        shutil.rmtree(tmp_root, ignore_errors=True)
    except Exception:  # noqa: BLE001
        pass

    print()
    if ok:
        print("==> 结论：旧版明文数据库可被当前版本无感知、零丢失地迁移为加密格式。VERIFIED OK")
        return 0
    print("==> 结论：存在校验未通过项，请检查上方 FAIL 行。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
