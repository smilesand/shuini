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

_SECRET = b'&\xd0E D\x85\x0c\xeb\x86\x06\xb2\x8b\xe2\x89K\x1eZ1\xe2\x9dS\xe6\xb8\x18\x181c\x0c\x87\x87.\x85'
_BLOB = 'kRXAa8M4EsQ5cKoqiB/QlebqD7ZgzYrCOBGnaZj1AtL5Na8zbOhEN9bG8r6zVgwPQr+5kv4e/spAqaAEuXETUR4ucf97LuU4QP4dn2lgsUI3qo0YC5u4/DbPBEpHn4VENEV5WKbpPjZYTAPhwG0L+Mw0K08LlvLvjvc4qzaYee4hYWoYfleJdz7SLbxdT5mNYVZOq2tFMaU5B/iIbj0o1o9tm60HOcW7PZnIN3DqSpkKJuPSlwpZw0fQyMnzO2lIAC7rOmzyeG54AgGiHcCI6QEnW+74qTBJXywIirTILQlo1YHlhA2OzBo16ncPT74qSadYDLfp4YUWVjpuR1TOQGT9QHPwrbT5San6sePrmDoKY9ZXnW6QLTvMllTODXcjQJqtbH9IZSUVOmio5SS4M5oau/r7HDqzNigywhPvcpfdd1vErdve8NQc0EcyhHk19QRnBJLNWrYFTdEE1fBXCJy4ADLVKR8yVZgA0Ih54qBRvo8PcOfmJnzmEB7g3nDVQwSwC+/g8RKwQoMN+z6Hk/D9sBie88ZtQa/jNp5r+fgg74pSmkD+2uQiaI8XAridSK+3JCuARPmMxPLEsN34C33iBA=='
_DIGEST = '4e6178479e901bcd8d363b21a8c908c03791a966397f2ef2bf6f45f71cb4b4dc'


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
