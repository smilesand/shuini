"""
初始化授权密钥与内嵌密钥模块（一次性）
========================================
生成一对全新的 RSA-2048 密钥，写入 ``scripts/keys/``（源头，由你自行管理与备份）：

    scripts/keys/private_key.pem   # 私钥源（签发授权码的唯一凭据）
    scripts/keys/public_key.pem    # 公钥源

随后把密钥以"混淆 + 完整性校验"的形式**编译进各客户端源码**，从而：

* 桌面端/后端 —— 内嵌公钥模块 ``backend/core/_license_pubkey.py``，被编译进后端
  可执行文件内部（不再是同级目录的明文文件）；
* 管理员授权端 —— 内嵌私钥的签发工具 ``release/license-tool/wtcmd-license-tool.py``，
  被编译进管理员 exe 内部。

两个内嵌模块都对密钥做了 XOR 混淆（每次生成使用随机密钥流）并附带 SHA-256 完整性
校验：任何对内嵌密钥的人为替换/篡改都会因校验失败而被程序拒绝。打包后的客户端仅信任
内嵌密钥，不再从磁盘文件或环境变量读取，普通用户无法替换。

⚠️ ``scripts/keys/private_key.pem`` 是签发授权码的唯一凭据，请离线妥善备份并保密：
一旦丢失，已签发的授权码将无法再被新生成的公钥校验。

用法::

    python scripts/init_license_keys.py            # 密钥已存在则跳过生成（仍刷新内嵌模块）
    python scripts/init_license_keys.py --force     # 强制重建密钥（会作废历史授权码）
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
KEYS_DIR = REPO_ROOT / "scripts" / "keys"
PRIVATE_KEY_PATH = KEYS_DIR / "private_key.pem"
PUBLIC_KEY_PATH = KEYS_DIR / "public_key.pem"
TOOL_PATH = REPO_ROOT / "release" / "license-tool" / "wtcmd-license-tool.py"
PUBKEY_MODULE_PATH = REPO_ROOT / "backend" / "core" / "_license_pubkey.py"
DB_KEY_PATH = KEYS_DIR / "db_key.bin"
DB_SECRET_MODULE_PATH = REPO_ROOT / "backend" / "core" / "_db_secret.py"


# ── 内嵌私钥的签发工具（管理员端） ────────────────────────────────────────
TOOL_HEADER = '''\
"""
单机版授权签发工具（内嵌混淆私钥）
====================================
私钥以 XOR 混淆 + SHA-256 完整性校验的形式编译在本文件内，运行时解码使用，
不读取任何外部密钥文件。对设备指纹签发授权码（RSA-PSS, MGF1-SHA256, max salt；
摘要 SHA-256），与后端 ``backend/core/license.py`` 的校验逻辑严格匹配。

⚠️ 本文件内嵌私钥，仅限授权方内部使用，切勿随产品或源码仓库分发。
   本文件由 scripts/init_license_keys.py 自动生成，请勿手改。

用法::

    python release/license-tool/wtcmd-license-tool.py issue --fp <FP> --days 365
"""

from __future__ import annotations
'''

TOOL_BODY = '''

import argparse
import base64
import hashlib
import json
from datetime import datetime, timedelta


def _keystream(n: int, secret: bytes) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < n:
        out.extend(hashlib.sha256(secret + counter.to_bytes(8, "big")).digest())
        counter += 1
    return bytes(out[:n])


def _load_private_key_pem() -> str:
    raw = base64.b64decode(_BLOB)
    keystream = _keystream(len(raw), _SECRET)
    pem_bytes = bytes(b ^ k for b, k in zip(raw, keystream))
    if hashlib.sha256(pem_bytes).hexdigest() != _DIGEST:
        raise ValueError("授权私钥完整性校验失败（疑似被人为替换/篡改）")
    return pem_bytes.decode("utf-8")


def _load_private_key():
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    return load_pem_private_key(_load_private_key_pem().encode("utf-8"), password=None)


def _make_license_payload(fingerprint: str, expiry: str) -> str:
    return json.dumps(
        {"v": 1, "fp": fingerprint.strip().upper(), "exp": expiry},
        ensure_ascii=False,
        sort_keys=True,
    )


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _sign_payload(payload: str, private_key) -> str:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    payload_bytes = payload.encode("utf-8")
    signature = private_key.sign(
        payload_bytes,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
    return _b64url(payload_bytes) + "." + _b64url(signature)


def issue(fingerprint: str, days: int):
    """返回 (授权码, 到期日期 YYYY-MM-DD)。"""
    expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    code = _sign_payload(_make_license_payload(fingerprint, expiry), _load_private_key())
    return code, expiry


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="授权码签发工具")
    sub = parser.add_subparsers(dest="command", required=True)
    p_issue = sub.add_parser("issue", help="为设备指纹签发授权码")
    p_issue.add_argument("--fp", required=True, help="设备指纹")
    p_issue.add_argument("--days", type=int, default=365, help="有效天数（默认 365）")
    args = parser.parse_args(argv)

    if args.command == "issue":
        code, expiry = issue(args.fp, args.days)
        print(f"fingerprint : {args.fp.strip().upper()}")
        print(f"expiry      : {expiry}")
        print(f"license_code: {code}")
        return 0
    parser.error(f"未知命令: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
'''


# ── 内嵌公钥模块（桌面端/后端） ──────────────────────────────────────────
PUBKEY_HEADER = '''\
"""
内嵌授权公钥（混淆 + 完整性校验）
==================================
公钥以 XOR 混淆 + SHA-256 完整性校验的形式编译在本模块内，由
``backend/core/license.py`` 在运行时解码并校验后用于授权码验签。

本模块被编译进后端可执行文件内部；任何对内嵌公钥的人为替换/篡改都会因完整性
校验失败而被拒绝，从而无法伪造授权码。

本文件由 scripts/init_license_keys.py 自动生成，请勿手改。
"""

from __future__ import annotations
'''

PUBKEY_BODY = '''

import base64
import hashlib


def _keystream(n: int, secret: bytes) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < n:
        out.extend(hashlib.sha256(secret + counter.to_bytes(8, "big")).digest())
        counter += 1
    return bytes(out[:n])


def load_public_key_pem() -> str:
    """解码并校验内嵌公钥 PEM；被篡改时抛出 ValueError。"""
    raw = base64.b64decode(_BLOB)
    keystream = _keystream(len(raw), _SECRET)
    pem_bytes = bytes(b ^ k for b, k in zip(raw, keystream))
    if hashlib.sha256(pem_bytes).hexdigest() != _DIGEST:
        raise ValueError("授权公钥完整性校验失败（疑似被人为替换/篡改）")
    return pem_bytes.decode("utf-8")
'''


# ── 内嵌数据库加密密钥模块（桌面端/后端） ────────────────────────────────
DBSECRET_HEADER = '''\
"""
内嵌数据库加密密钥（混淆 + 完整性校验）
========================================
AES-256-GCM 主密钥以 XOR 混淆 + SHA-256 完整性校验的形式编译在本模块内，
由 ``backend/core/secure_db.py`` 在运行时解码后用于整库加解密与 license_state 防篡改 HMAC。

本模块被编译进后端可执行文件内部；任何对内嵌密钥的人为替换/篡改都会因完整性校验失败而被拒绝。

本文件由 scripts/init_license_keys.py 自动生成，请勿手改。
"""

from __future__ import annotations
'''

DBSECRET_BODY = '''

import base64
import hashlib


def _keystream(n: int, secret: bytes) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < n:
        out.extend(hashlib.sha256(secret + counter.to_bytes(8, "big")).digest())
        counter += 1
    return bytes(out[:n])


def load_db_key() -> bytes:
    """解码并校验内嵌数据库主密钥（32 字节）；被篡改时抛出 ValueError。"""
    raw = base64.b64decode(_BLOB)
    keystream = _keystream(len(raw), _SECRET)
    key = bytes(b ^ k for b, k in zip(raw, keystream))
    if hashlib.sha256(key).hexdigest() != _DIGEST:
        raise ValueError("数据库主密钥完整性校验失败（疑似被人为替换/篡改）")
    return key
'''


def _keystream(n: int, secret: bytes) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < n:
        out.extend(hashlib.sha256(secret + counter.to_bytes(8, "big")).digest())
        counter += 1
    return bytes(out[:n])


def _render_embedded(plaintext: bytes) -> str:
    """把明文密钥渲染为 ``_SECRET/_BLOB/_DIGEST`` 三行（随机密钥流混淆）。"""
    secret = os.urandom(32)
    keystream = _keystream(len(plaintext), secret)
    blob = bytes(b ^ k for b, k in zip(plaintext, keystream))
    blob_b64 = base64.b64encode(blob).decode("ascii")
    digest = hashlib.sha256(plaintext).hexdigest()
    return f"\n_SECRET = {secret!r}\n_BLOB = {blob_b64!r}\n_DIGEST = {digest!r}\n"


def _generate_keypair() -> tuple[str, str]:
    """返回 (私钥 PEM, 公钥 PEM)。"""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    return private_pem, public_pem


def derive_public_pem(private_pem: str) -> str:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    key = load_pem_private_key(private_pem.encode("utf-8"), password=None)
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")


def write_signing_tool(private_pem: str) -> None:
    """写出内嵌混淆私钥的签发工具（管理员端）。"""
    TOOL_PATH.parent.mkdir(parents=True, exist_ok=True)
    text = TOOL_HEADER + _render_embedded(private_pem.encode("utf-8")) + TOOL_BODY
    TOOL_PATH.write_text(text, encoding="utf-8")


def write_public_module(public_pem: str) -> None:
    """写出内嵌混淆公钥模块（桌面端/后端）。"""
    PUBKEY_MODULE_PATH.parent.mkdir(parents=True, exist_ok=True)
    text = PUBKEY_HEADER + _render_embedded(public_pem.encode("utf-8")) + PUBKEY_BODY
    PUBKEY_MODULE_PATH.write_text(text, encoding="utf-8")


def sync_public_module() -> str:
    """从 scripts/keys/private_key.pem 派生公钥并刷新内嵌公钥模块与公钥源文件。"""
    private_pem = PRIVATE_KEY_PATH.read_text(encoding="utf-8")
    public_pem = derive_public_pem(private_pem)
    write_public_module(public_pem)
    PUBLIC_KEY_PATH.write_text(public_pem, encoding="utf-8")
    return public_pem


def _generate_db_key() -> bytes:
    """生成 32 字节随机 AES-256 主密钥。"""
    return os.urandom(32)


def write_db_secret_module(db_key: bytes) -> None:
    """写出内嵌混淆的数据库主密钥模块（桌面端/后端）。"""
    DB_SECRET_MODULE_PATH.parent.mkdir(parents=True, exist_ok=True)
    text = DBSECRET_HEADER + _render_embedded(db_key) + DBSECRET_BODY
    DB_SECRET_MODULE_PATH.write_text(text, encoding="utf-8")


def sync_db_secret_module() -> bytes:
    """从 scripts/keys/db_key.bin 刷新内嵌数据库密钥模块。"""
    db_key = DB_KEY_PATH.read_bytes()
    write_db_secret_module(db_key)
    return db_key


def main() -> int:
    parser = argparse.ArgumentParser(description="生成授权密钥与内嵌密钥模块（一次性）")
    parser.add_argument(
        "--force", action="store_true", help="强制重建密钥（会作废历史授权码）"
    )
    args = parser.parse_args()

    KEYS_DIR.mkdir(parents=True, exist_ok=True)

    if PRIVATE_KEY_PATH.exists() and not args.force:
        print(f"[i] 私钥源已存在，跳过生成: {PRIVATE_KEY_PATH}")
        print("   如需重建（会作废历史授权码），请加 --force。")
    else:
        private_pem, public_pem = _generate_keypair()
        PRIVATE_KEY_PATH.write_text(private_pem, encoding="utf-8")
        PUBLIC_KEY_PATH.write_text(public_pem, encoding="utf-8")
        print(f"[ok] 已生成私钥源: {PRIVATE_KEY_PATH}")
        print(f"[ok] 已生成公钥源: {PUBLIC_KEY_PATH}")

    private_pem = PRIVATE_KEY_PATH.read_text(encoding="utf-8")

    # 管理员端：内嵌混淆私钥的签发工具。
    write_signing_tool(private_pem)
    print(f"[ok] 已写出内嵌混淆私钥的签发工具: {TOOL_PATH}")

    # 桌面端/后端：内嵌混淆公钥模块。
    sync_public_module()
    print(f"[ok] 已写出内嵌混淆公钥模块: {PUBKEY_MODULE_PATH}")

    # 数据库整库加密主密钥（独立生命周期：仅在不存在时生成，避免重建时作废已有客户数据）。
    if not DB_KEY_PATH.exists():
        DB_KEY_PATH.write_bytes(_generate_db_key())
        print(f"[ok] 已生成数据库主密钥源: {DB_KEY_PATH}")
    else:
        print(f"[ok] 数据库主密钥源已存在，保留以免作废客户数据: {DB_KEY_PATH}")
    sync_db_secret_module()
    print(f"[ok] 已写出内嵌混淆数据库密钥模块: {DB_SECRET_MODULE_PATH}")

    print(
        "\n完成。内嵌密钥已编译进各端源码（混淆 + 完整性校验，普通用户无法替换）。"
        "\n请离线妥善备份并保密 scripts/keys/private_key.pem（签发授权码的唯一凭据）。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
