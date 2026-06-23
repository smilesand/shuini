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

_SECRET = b'\x94\x0fj"\xb6\x90\xa2\x99\x92"k\x11lk\xcf\xaf\nb\xb4\xcc\xd6\xe7H\xcf\xaa\xa7U8\xd9\xd9\xe7&'
_BLOB = 'X+bIx76Cb6KONcwqMd9MYK7U2+hgwzYWYbfNxe00cp7rocIxcl16PIOVOW9MGhQrUCjVs6UFktlR+lfUeIO9ldOBNIooXBOWhca6BUIi3ZXx5rgnZ0GJ05Zl+UKHieZs7Bql0zaA0nTPCCr4uwDgMkIN/nfwLMH22oLqcnmgec53P17MOAURnK9qSBA2VDl27vGnKhBcqNkqrEXh1d2YBZhC+r1s9lMLhxtVLnPoI0/bLZbOIDk/xLzSTBJpKhJG3/xUnvVZRSrX6eGI8zsxpP12CZxRf5qrFmfno9QFpITfmSXY4DQ9nIjWkA9dylkQhRl9ilsvzA8R1/NpgaPyeoHdcybjHWBWYnpY0Zmgv11Oek1EhAOx4pZui00VeZw1izcsHy9FBgHeA7Fy4KKadkvKVNKElxKu7HUBlJjkt/ZSpM/OIaRt40/ySoYltEsUH8OELSQwHqpYqPNhMI5VBnrq2oOKWOXIe2K3UBdL9SAYMtS51BGleVXgbuKtt+yMZv4ETRY2aB/WffyTXOqZBfFk4uPaCAyKHkf+yq4tBYmMwe0O0Br2aKppI7zCPtIspOKsqzuxEQGYzsdBNWNHizOHYw=='
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
