"""
整库加密与防篡改工具
====================
为单机版桌面客户端提供 SQLite 数据库的**整文件加密**与 license_state **防篡改 HMAC**。

* 加密：AES-256-GCM。主密钥来自编译进后端内部的内嵌混淆模块 ``core._db_secret``，
  普通用户无法替换/读取。磁盘上始终只有密文，DBeaver 等工具无法直接打开。
* 文件格式::

      MAGIC(8) || NONCE(12) || AES-GCM(密文 + 16 字节认证标签)

  其中 GCM 的附加认证数据(AAD)固定为 MAGIC，任何对头部或密文的篡改都会在解密时被发现。
* license_state 防篡改：对受保护字段计算 HMAC-SHA256（密钥同为数据库主密钥），
  存入 ``guard`` 列；读取时校验，发现不一致即判定为人为篡改。

开发者解密通道见 ``scripts/decrypt_db.py``（使用 ``scripts/keys/db_key.bin`` 解密）。
"""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Optional

MAGIC = b"WTSCDB01"
_NONCE_LEN = 12


def _load_key() -> bytes:
    """加载内嵌数据库主密钥（32 字节）。被篡改时由内嵌模块抛出 ValueError。"""
    from core import _db_secret  # 延迟导入：未生成时不影响其它逻辑

    return _db_secret.load_db_key()


# ── 整库加解密 ────────────────────────────────────────────────────────────
def encrypt(plaintext: bytes, key: Optional[bytes] = None) -> bytes:
    """把明文（SQLite 序列化字节）加密为带头部的密文 blob。"""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if key is None:
        key = _load_key()
    nonce = os.urandom(_NONCE_LEN)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, MAGIC)
    return MAGIC + nonce + ciphertext


def decrypt(blob: bytes, key: Optional[bytes] = None) -> bytes:
    """校验头部并解密，返回明文（SQLite 序列化字节）。

    blob 非法或被篡改时抛出异常（``ValueError`` 或 cryptography 的 ``InvalidTag``）。
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if len(blob) < len(MAGIC) + _NONCE_LEN:
        raise ValueError("加密数据库文件过短或损坏")
    if blob[: len(MAGIC)] != MAGIC:
        raise ValueError("不是有效的加密数据库文件（头部不匹配）")
    nonce = blob[len(MAGIC) : len(MAGIC) + _NONCE_LEN]
    ciphertext = blob[len(MAGIC) + _NONCE_LEN :]
    if key is None:
        key = _load_key()
    return AESGCM(key).decrypt(nonce, ciphertext, MAGIC)


def is_encrypted_blob(head: bytes) -> bool:
    return head[: len(MAGIC)] == MAGIC


def encrypt_to_file(path: str, plaintext: bytes, key: Optional[bytes] = None) -> None:
    """原子写入：先写临时文件并 fsync，再 os.replace 覆盖目标，避免写入中途损坏。"""
    data = encrypt(plaintext, key)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


# ── license_state 防篡改 HMAC ──────────────────────────────────────────────
def license_guard(
    fingerprint: Optional[str],
    license_code: Optional[str],
    expiry: Optional[str],
    activated_at: Optional[str],
    first_seen: Optional[str],
    key: Optional[bytes] = None,
) -> str:
    """对 license_state 受保护字段计算 HMAC-SHA256（十六进制）。"""
    if key is None:
        key = _load_key()
    msg = "\x1f".join(
        "" if v is None else str(v)
        for v in (fingerprint, license_code, expiry, activated_at, first_seen)
    ).encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()
