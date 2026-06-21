"""测试辅助：手动“快进”桌面版试用期，无需等待真实 3 天。

试用期是按数据库 ``license_state`` 表中的 ``first_seen``（首次启动时间）+ 3 天计算的。
本脚本把 ``first_seen`` 改成 N 天前，即可立刻让试用期到期/还剩若干天，方便测试
“未授权客户端到期后是否可用”。

用法（在仓库根目录运行）::

    # 让试用期立刻过期（first_seen 设为 4 天前 > 3 天试用）
    python scripts/expire_trial.py

    # 指定还剩 1 天（first_seen 设为 2 天前）
    python scripts/expire_trial.py --days-ago 2

    # 指定数据库路径（默认自动定位桌面版 userData 下的 data.db）
    python scripts/expire_trial.py --db "C:\\Users\\me\\AppData\\Roaming\\wtcmd-platform-desktop\\data.db"

注意：必须先把桌面版至少启动过一次（生成 data.db 与 license_state 行）。
若该机已激活（license_code 不为空），脚本会提示并可加 --clear-activation 清除激活以测试试用。
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path

import decrypt_db


def default_db_path() -> Path:
    """桌面版默认把 data.db 放在 Electron userData 目录。

    Electron 的 userData = ``%APPDATA%\\<productName>``，本产品 productName 为
    ``WTCMD Platform``（见 desktop/package.json）。为兼容历史/不同命名，按存在性
    依次探测候选目录。
    """
    appdata = os.getenv("APPDATA")
    if appdata:
        candidates = [
            Path(appdata) / "WTCMD Platform" / "data.db",
            Path(appdata) / "wtcmd-platform-desktop" / "data.db",
        ]
        for cand in candidates:
            if cand.is_file():
                return cand
        return candidates[0]
    return Path.cwd() / "data.db"


def main() -> int:
    parser = argparse.ArgumentParser(description="快进桌面版试用期用于测试")
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="data.db 路径，默认自动定位桌面版 userData 下的 data.db",
    )
    parser.add_argument(
        "--days-ago",
        type=int,
        default=4,
        help="将 first_seen 设为 N 天前（默认 4，>3 即立刻过期；填 2 则还剩 1 天）",
    )
    parser.add_argument(
        "--clear-activation",
        action="store_true",
        help="同时清除已保存的授权码（license_code），以便回到试用状态测试",
    )
    args = parser.parse_args()

    db_path = args.db or default_db_path()
    if not db_path.is_file():
        print(f"[!] 找不到数据库：{db_path}")
        print("    请先启动一次桌面版生成 data.db，或用 --db 指定正确路径。")
        return 1

    new_first_seen = (datetime.now().replace(microsecond=0) - timedelta(days=args.days_ago)).isoformat()

    # 数据库是整库加密的：先用主密钥读入内存，改完再加密写回，并重算防篡改 guard。
    key = decrypt_db.load_db_key()
    conn = decrypt_db.open_in_memory(db_path, key)
    try:
        row = conn.execute(
            "SELECT fingerprint, license_code, expiry, activated_at, first_seen FROM license_state WHERE id=1"
        ).fetchone()
        if row is None:
            print("[!] license_state 尚无数据行，请先启动一次桌面版后再运行本脚本。")
            return 1

        fingerprint = row["fingerprint"]
        license_code = row["license_code"]
        old_first_seen = row["first_seen"]
        if args.clear_activation:
            license_code = None
            expiry = None
            activated_at = None
            conn.execute(
                "UPDATE license_state SET first_seen=?, last_seen=?, license_code=NULL, "
                "expiry=NULL, activated_at=NULL WHERE id=1",
                (new_first_seen, new_first_seen),
            )
        else:
            expiry = row["expiry"]
            activated_at = row["activated_at"]
            conn.execute(
                "UPDATE license_state SET first_seen=?, last_seen=? WHERE id=1",
                (new_first_seen, new_first_seen),
            )
        # 重算防篡改 guard，否则后端会判定为被篡改而锁定。
        guard = decrypt_db.license_guard(
            key, fingerprint, license_code, expiry, activated_at, new_first_seen
        )
        conn.execute("UPDATE license_state SET guard=? WHERE id=1", (guard,))
        conn.commit()
        decrypt_db.save_encrypted(conn, db_path, key)

        print(f"[ok] 数据库：{db_path}")
        print(f"     指纹：{fingerprint}")
        print(f"     first_seen：{old_first_seen}  ->  {new_first_seen}（{args.days_ago} 天前）")
        if license_code and not args.clear_activation:
            print("[!] 注意：该机已保存授权码（已激活），试用期判断不会生效。")
            print("    如需测试试用到期，请加 --clear-activation 清除激活。")
        elif args.clear_activation and row["license_code"]:
            print("     已清除原有激活授权码，现处于试用状态。")
        print()
        print("下一步：重启桌面版（或重新调用 /api/license/status），即可看到试用期变化。")
        print("  - days-ago > 3  → 试用期已结束，客户端应拦截使用。")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
