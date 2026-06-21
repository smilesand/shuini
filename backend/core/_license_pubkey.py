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

_SECRET = b'kX\xe1q<U\xcd\x05\x12Z#\n_K$\x91\x08\xc6\xa9d\xb8\xac\x82Yi\x1a\x0f* \xc8\x8f\x04'
_BLOB = 'dRCJlOWoyfdvhBwIg/x9wNQfEWuJziTvUDV5MvNJ8vqC9Ur2fogq9b/ixwRW9fk88CVjJCr5fYlBdtn33tB3+cahKjRdd1qE+VdgWppmqKDWyoFVv31EmoQhid7zkY9vjhR8qHFbIBsqPmTR/+3afH2UjIubKkS00N2GgZg15UD8AG8L9lXB0JeMM2qc4x16UfeIfS7JtwFIpV2IUZO/SQmFvmP9iWZWubIQFzY1/Fg9vOptXjbH1VgA/DBJrJnylUlygxOZX2h5c8YEreCDtSQFiD1bRpjws1inB9PmKDdmbxx0VNjEqQLwA/SteoFdd4etwSheaULEwL+mnDiXymSBIxnTe9Ju/YqNIDQAo9SEbOZEbX5khVvA2/5/GfbhBsyqPJAdzTNMliGdgvS34JX9TW0gEXPPfNftDA8HiXzOif9zT0snK7ZTnHbZL88Y+ePzNqzRT2hl1prHBNoMdt/MREex5OkQNHanZJlp/SDHCtA/7cEDMkt7mpQaXDYpIluOKaSnihJz5bWjEGp9BRTbImCAbqQYKTd64Vzz6ZxgHakzIa1GMkcCiBS2XozPGg92UKpPU1+yR+qKLXenaUYfHw=='
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
