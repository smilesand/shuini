"""开发者数据库解密 / 加密工具
================================
客户端 ``data.db`` 在磁盘上是 **AES-256-GCM 整库加密** 的（DBeaver 等工具无法直接打开）。
本工具供开发/运维人员用主密钥解开数据库，排查或修改数据后可再加密写回。

主密钥来源（按优先级）：
  1. ``scripts/keys/db_key.bin``（仓库内 32 字节原始密钥，开发机持有）
  2. 后端内嵌混淆模块 ``backend/core/_db_secret.py``（兜底）

用法（在仓库根目录运行）::

    # 1) 把加密库解密成明文 sqlite，可直接用 DBeaver / sqlite3 打开
    python scripts/decrypt_db.py decrypt --in  "%APPDATA%\\WTCMD Platform\\data.db" \
                                         --out  plain.db

    # 2) 改完明文库后再加密写回（覆盖客户端加密库）
    python scripts/decrypt_db.py encrypt --in  plain.db \
                                         --out  "%APPDATA%\\WTCMD Platform\\data.db"

    # 3) 直接查看 license_state（无需先落地明文文件）
    python scripts/decrypt_db.py show --in "%APPDATA%\\WTCMD Platform\\data.db"
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_KEY_PATH = REPO_ROOT / "scripts" / "keys" / "db_key.bin"
BACKEND_DIR = REPO_ROOT / "backend"

MAGIC = b"WTSCDB01"
_NONCE_LEN = 12
_SQLITE_MAGIC = b"SQLite format 3\x00"


def _frozen_bundle_key() -> "bytes | None":
    """打包成 exe 后，主密钥 db_key.bin 以数据文件形式内嵌在 PyInstaller 解压目录中。"""
    base = getattr(sys, "_MEIPASS", None)
    if not base:
        return None
    bundled = Path(base) / "db_key.bin"
    if not bundled.is_file():
        return None
    key = bundled.read_bytes()
    if len(key) != 32:
        raise ValueError(f"内嵌主密钥长度异常（应为 32 字节）：{bundled}")
    return key


def load_db_key() -> bytes:
    """读取数据库主密钥。

    优先级：
      1. 打包 exe 内嵌的 db_key.bin（``sys._MEIPASS``）；
      2. 仓库内 ``scripts/keys/db_key.bin``（开发机）；
      3. 后端内嵌混淆模块 ``backend/core/_db_secret.py``（兜底）。
    """
    bundled = _frozen_bundle_key()
    if bundled is not None:
        return bundled
    if DB_KEY_PATH.is_file():
        key = DB_KEY_PATH.read_bytes()
        if len(key) != 32:
            raise ValueError(f"{DB_KEY_PATH} 长度异常（应为 32 字节）")
        return key
    # 兜底：从内嵌混淆模块解码
    sys.path.insert(0, str(BACKEND_DIR))
    try:
        from core import _db_secret  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            f"[!] 找不到主密钥：{DB_KEY_PATH} 不存在，且无法加载内嵌模块 ({exc})。\n"
            "    请先运行 python scripts/init_license_keys.py 生成密钥。"
        ) from exc
    return _db_secret.load_db_key()


def decrypt_blob(blob: bytes, key: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if blob[: len(MAGIC)] != MAGIC:
        raise ValueError("不是有效的加密数据库文件（头部不匹配）")
    nonce = blob[len(MAGIC) : len(MAGIC) + _NONCE_LEN]
    ciphertext = blob[len(MAGIC) + _NONCE_LEN :]
    return AESGCM(key).decrypt(nonce, ciphertext, MAGIC)


def encrypt_bytes(plaintext: bytes, key: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = os.urandom(_NONCE_LEN)
    return MAGIC + nonce + AESGCM(key).encrypt(nonce, plaintext, MAGIC)


def read_snapshot(path: Path, key: bytes) -> bytes:
    """读取任意形态(加密/旧版明文)数据库，返回明文 SQLite 序列化字节。"""
    blob = path.read_bytes()
    head = blob[:16]
    if head[: len(MAGIC)] == MAGIC:
        return decrypt_blob(blob, key)
    if head == _SQLITE_MAGIC:
        return blob  # 已是明文 sqlite 文件
    raise ValueError(f"无法识别的数据库文件：{path}")


def license_guard(key: bytes, fingerprint, license_code, expiry, activated_at, first_seen) -> str:
    msg = "\x1f".join(
        "" if v is None else str(v)
        for v in (fingerprint, license_code, expiry, activated_at, first_seen)
    ).encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def open_in_memory(path: Path, key: bytes) -> sqlite3.Connection:
    """把磁盘上的(加密)库读入内存 sqlite 连接，便于程序化修改后再加密写回。"""
    snapshot = read_snapshot(path, key)
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.deserialize(snapshot)
    return conn


def save_encrypted(conn: sqlite3.Connection, path: Path, key: bytes) -> None:
    """把内存连接序列化、加密后原子写回磁盘。"""
    snapshot = bytes(conn.serialize())
    blob = encrypt_bytes(snapshot, key)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as f:
        f.write(blob)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _cmd_decrypt(args) -> int:
    key = load_db_key()
    snapshot = read_snapshot(Path(args.inp), key)
    Path(args.out).write_bytes(snapshot)
    print(f"[ok] 已解密为明文 sqlite：{args.out}")
    print("     可用 DBeaver / sqlite3 直接打开。改完后用 encrypt 子命令写回。")
    return 0


def _cmd_encrypt(args) -> int:
    key = load_db_key()
    plaintext = Path(args.inp).read_bytes()
    if plaintext[:16] != _SQLITE_MAGIC:
        print("[!] 输入文件不是明文 sqlite，已中止（避免二次加密）。")
        return 1
    blob = encrypt_bytes(plaintext, key)
    Path(args.out).write_bytes(blob)
    print(f"[ok] 已加密写回：{args.out}")
    return 0


def _cmd_show(args) -> int:
    key = load_db_key()
    conn = open_in_memory(Path(args.inp), key)
    try:
        row = conn.execute(
            "SELECT fingerprint, license_code, expiry, activated_at, first_seen, last_seen, guard "
            "FROM license_state WHERE id=1"
        ).fetchone()
    except sqlite3.OperationalError as exc:
        print(f"[!] 读取 license_state 失败：{exc}")
        return 1
    finally:
        conn.close()
    if row is None:
        print("[i] license_state 暂无数据行。")
        return 0
    d = dict(row)
    print("license_state:")
    for k in ("fingerprint", "license_code", "expiry", "activated_at", "first_seen", "last_seen"):
        print(f"  {k:13}: {d.get(k)}")
    stored = d.get("guard")
    if stored:
        expected = license_guard(
            key, d.get("fingerprint"), d.get("license_code"), d.get("expiry"),
            d.get("activated_at"), d.get("first_seen"),
        )
        print(f"  guard        : {'OK 未被篡改' if stored == expected else '!! 不匹配（疑似被篡改）'}")
    else:
        print("  guard        : (空，未启用防篡改/旧库)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="开发者数据库解密/加密工具")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_dec = sub.add_parser("decrypt", help="加密库 -> 明文 sqlite")
    p_dec.add_argument("--in", dest="inp", required=True, help="加密的 data.db 路径")
    p_dec.add_argument("--out", required=True, help="输出明文 sqlite 路径")
    p_dec.set_defaults(func=_cmd_decrypt)

    p_enc = sub.add_parser("encrypt", help="明文 sqlite -> 加密库")
    p_enc.add_argument("--in", dest="inp", required=True, help="明文 sqlite 路径")
    p_enc.add_argument("--out", required=True, help="输出加密 data.db 路径")
    p_enc.set_defaults(func=_cmd_encrypt)

    p_show = sub.add_parser("show", help="直接查看 license_state（含防篡改校验）")
    p_show.add_argument("--in", dest="inp", required=True, help="加密的 data.db 路径")
    p_show.set_defaults(func=_cmd_show)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
