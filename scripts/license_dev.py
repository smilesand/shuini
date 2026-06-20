"""
授权状态测试工具（仅供开发/测试，切勿随产品分发）
====================================================
桌面/单机版的试用期为 3 天（``backend/core/license.py`` 中 ``TRIAL_DAYS``）。
为了在不等待 3 天的情况下验证"试用到期 → 锁定 → 激活"流程，本脚本直接修改
SQLite 中的 ``license_state`` 单行表，模拟不同的授权状态。

它复用后端完全相同的试用计算口径：``trial_end = first_seen + TRIAL_DAYS``，
``effective_now = max(now, last_seen)``（防时钟回拨）。因此修改 ``first_seen`` /
``last_seen`` 即可精确控制"剩余天数"。

子命令::

    python scripts/license_dev.py show                 # 查看当前状态与剩余天数
    python scripts/license_dev.py set-days 1           # 把剩余试用天数设为 1 天
    python scripts/license_dev.py expire               # 立即把试用置为已到期（锁定）
    python scripts/license_dev.py reset                # 恢复为全新 3 天试用
    python scripts/license_dev.py expire-license       # 模拟"已激活但授权码过期"后被锁定

数据库定位（按优先级）::

    1. --db <路径> 显式指定
    2. 桌面版安装后默认数据库： %APPDATA%\\WTCMD Platform\\data.db
    3. 旧版应用名目录：          %APPDATA%\\wtcmd-platform-desktop\\data.db
    4. 源码调试数据库：           backend/data.db

修改后，重新打开桌面应用（或等待前端再次轮询 /api/license/status）即可看到效果。
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# 与 backend/core/license.py 的 TRIAL_DAYS 保持一致。
TRIAL_DAYS = 3


def _candidate_db_paths() -> list[Path]:
    paths: list[Path] = []
    appdata = os.getenv("APPDATA")
    if appdata:
        paths.append(Path(appdata) / "WTCMD Platform" / "data.db")
        paths.append(Path(appdata) / "wtcmd-platform-desktop" / "data.db")
    paths.append(REPO_ROOT / "backend" / "data.db")
    return paths


def _resolve_db(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise SystemExit(f"指定的数据库不存在: {path}")
        return path

    for candidate in _candidate_db_paths():
        if candidate.is_file():
            return candidate

    listed = "\n".join(f"    - {p}" for p in _candidate_db_paths())
    raise SystemExit(
        "未自动找到数据库，请用 --db 指定其路径。已尝试：\n" + listed
    )


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_row(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT id FROM license_state WHERE id=1").fetchone()
    if row is None:
        now = _iso(datetime.now())
        conn.execute(
            "INSERT INTO license_state (id, fingerprint, license_code, expiry, "
            "activated_at, first_seen, last_seen) VALUES (1, '', NULL, NULL, NULL, ?, ?)",
            (now, now),
        )
        conn.commit()


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _compute_days_left(first_seen: datetime | None, last_seen: datetime | None) -> int:
    now = datetime.now().replace(microsecond=0)
    first_seen = first_seen or now
    effective_now = max(now, last_seen or now)
    remaining = (first_seen + timedelta(days=TRIAL_DAYS)) - effective_now
    if remaining.total_seconds() <= 0:
        return 0
    return max(0, remaining.days + (1 if remaining.seconds or remaining.microseconds else 0))


def cmd_show(conn: sqlite3.Connection) -> None:
    _ensure_row(conn)
    row = conn.execute(
        "SELECT fingerprint, license_code, expiry, activated_at, first_seen, last_seen "
        "FROM license_state WHERE id=1"
    ).fetchone()
    first_seen = _parse(row["first_seen"])
    last_seen = _parse(row["last_seen"])
    days_left = _compute_days_left(first_seen, last_seen)
    activated = bool(row["license_code"])

    print("当前 license_state：")
    print(f"  fingerprint : {row['fingerprint']}")
    print(f"  license_code: {row['license_code'] or '（无，处于试用）'}")
    print(f"  expiry      : {row['expiry'] or '-'}")
    print(f"  activated_at: {row['activated_at'] or '-'}")
    print(f"  first_seen  : {row['first_seen']}")
    print(f"  last_seen   : {row['last_seen']}")
    print("推算授权判定（与后端口径一致）：")
    if activated:
        print("  已写入授权码 → 由后端按签名/到期日校验，过期则回退试用判断")
    print(f"  trial_days_left = {days_left}")
    print(f"  can_use(试用)   = {days_left > 0}")


def cmd_set_days(conn: sqlite3.Connection, days_left: int) -> None:
    if not 0 <= days_left <= TRIAL_DAYS:
        raise SystemExit(f"剩余天数需在 0..{TRIAL_DAYS} 之间")
    _ensure_row(conn)
    now = datetime.now().replace(microsecond=0)
    first_seen = now - timedelta(days=(TRIAL_DAYS - days_left))
    conn.execute(
        "UPDATE license_state SET first_seen=?, last_seen=?, license_code=NULL, "
        "expiry=NULL, activated_at=NULL WHERE id=1",
        (_iso(first_seen), _iso(now)),
    )
    conn.commit()
    print(f"已将试用剩余天数设为 {days_left} 天（first_seen={_iso(first_seen)}）。")


def cmd_expire(conn: sqlite3.Connection) -> None:
    _ensure_row(conn)
    now = datetime.now().replace(microsecond=0)
    first_seen = now - timedelta(days=TRIAL_DAYS + 1)
    conn.execute(
        "UPDATE license_state SET first_seen=?, last_seen=?, license_code=NULL, "
        "expiry=NULL, activated_at=NULL WHERE id=1",
        (_iso(first_seen), _iso(now)),
    )
    conn.commit()
    print("已将试用期置为【已到期】，应用应锁定并跳转激活页。")


def cmd_expire_license(conn: sqlite3.Connection) -> None:
    _ensure_row(conn)
    now = datetime.now().replace(microsecond=0)
    first_seen = now - timedelta(days=TRIAL_DAYS + 1)
    past_expiry = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    # 写入一个已过期的占位授权码：后端校验失败 → 回退试用判断 → 试用亦到期 → 锁定。
    conn.execute(
        "UPDATE license_state SET license_code=?, expiry=?, activated_at=?, "
        "first_seen=?, last_seen=? WHERE id=1",
        ("EXPIRED.DEMO", past_expiry, _iso(now - timedelta(days=400)),
         _iso(first_seen), _iso(now)),
    )
    conn.commit()
    print("已模拟【授权码过期 + 试用到期】状态，应用应锁定并跳转激活页。")


def cmd_reset(conn: sqlite3.Connection) -> None:
    now = datetime.now().replace(microsecond=0)
    conn.execute("DELETE FROM license_state WHERE id=1")
    conn.execute(
        "INSERT INTO license_state (id, fingerprint, license_code, expiry, "
        "activated_at, first_seen, last_seen) VALUES (1, '', NULL, NULL, NULL, ?, ?)",
        (_iso(now), _iso(now)),
    )
    conn.commit()
    print(f"已重置为全新 {TRIAL_DAYS} 天试用。")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="授权状态测试工具（开发用）")
    parser.add_argument("--db", help="data.db 路径（默认自动探测桌面安装目录）")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("show", help="查看当前授权状态")
    p_set = sub.add_parser("set-days", help="设置试用剩余天数")
    p_set.add_argument("days", type=int, help=f"剩余天数 0..{TRIAL_DAYS}")
    sub.add_parser("expire", help="立即将试用置为已到期（锁定）")
    sub.add_parser("expire-license", help="模拟已激活但授权码过期后的锁定")
    sub.add_parser("reset", help="恢复为全新试用")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    db_path = _resolve_db(args.db)
    print(f"数据库: {db_path}\n")

    conn = _connect(db_path)
    try:
        if args.command == "show":
            cmd_show(conn)
        elif args.command == "set-days":
            cmd_set_days(conn, args.days)
            print()
            cmd_show(conn)
        elif args.command == "expire":
            cmd_expire(conn)
            print()
            cmd_show(conn)
        elif args.command == "expire-license":
            cmd_expire_license(conn)
        elif args.command == "reset":
            cmd_reset(conn)
            print()
            cmd_show(conn)
        else:  # pragma: no cover - argparse 已保证
            raise SystemExit(f"未知命令: {args.command}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
