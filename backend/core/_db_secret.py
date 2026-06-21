"""
内嵌数据库加密密钥（混淆 + 完整性校验）
========================================
AES-256-GCM 主密钥以 XOR 混淆 + SHA-256 完整性校验的形式编译在本模块内，
由 ``backend/core/secure_db.py`` 在运行时解码后用于整库加解密与 license_state 防篡改 HMAC。

本模块被编译进后端可执行文件内部；任何对内嵌密钥的人为替换/篡改都会因完整性校验失败而被拒绝。

本文件由 scripts/init_license_keys.py 自动生成，请勿手改。
"""

from __future__ import annotations

_SECRET = b'\xd1\x16\xd1\x04\x06"\xd8\x93\xf5J\xb1\x14\x19\x88\x11\xd2\x16\x1d\x93=\xb5\xa8\x95m\xb1\xed\xe9\x9e\xe2\x85\x13f'
_BLOB = 'UgxaAwvY3jejsNhTkfXt1tjwzwxJiH+jBxOIhySG164='
_DIGEST = 'b99c0357c5416e38d7da68f93e8f33edec796c6e9048d8ad1624723dd6fe8f64'


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
