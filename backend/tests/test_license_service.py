"""授权核心单元测试。

运行（在 backend/ 目录下）::

    python -m unittest tests.test_license_service
"""

import base64
import importlib
import json
import os
import tempfile
import unittest
from datetime import date, timedelta

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

# ── 生成一对临时 RSA 密钥，作为本次测试的"签发工具" ──────────────────────
_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUBLIC_PEM = _PRIVATE_KEY.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode("ascii")

_FINGERPRINT = "ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789"

# ── 在导入后端模块前固定环境（get_settings 使用 lru_cache）──────────────────
_TMP_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TMP_DB.close()
os.environ["SC_EDITION"] = "desktop"
os.environ["SC_LICENSE_FINGERPRINT"] = _FINGERPRINT
os.environ["SC_LICENSE_PUBLIC_KEY_PEM"] = _PUBLIC_PEM
os.environ["SC_DB_PATH"] = _TMP_DB.name

import database  # noqa: E402
from core import license as lic  # noqa: E402


def _make_code(fingerprint: str, expiry: str) -> str:
    """复刻签发工具的授权码格式：base64url(payload).base64url(sig)。"""
    payload = {"v": 1, "fp": fingerprint.upper(), "exp": expiry}
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    signature = _PRIVATE_KEY.sign(
        payload_json.encode("utf-8"),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
    p = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("ascii").rstrip("=")
    s = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{p}.{s}"


def _future(days: int = 365) -> str:
    return (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")


def _reset_state(first_seen: str | None = None, last_seen: str | None = None) -> None:
    conn = database.get_db()
    try:
        conn.execute("DELETE FROM license_state")
        if first_seen is not None or last_seen is not None:
            conn.execute(
                "INSERT INTO license_state (id, fingerprint, first_seen, last_seen) "
                "VALUES (1, ?, ?, ?)",
                (_FINGERPRINT, first_seen, last_seen),
            )
        conn.commit()
    finally:
        conn.close()


class LicenseCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()

    def setUp(self):
        _reset_state()

    # ── 授权码校验 ──────────────────────────────────────────────
    def test_verify_valid_code(self):
        code = _make_code(_FINGERPRINT, _future())
        result = lic.verify_license_code(code, _FINGERPRINT)
        self.assertTrue(result["valid"], result["reason"])

    def test_verify_wrong_fingerprint(self):
        code = _make_code("0" * 64, _future())
        result = lic.verify_license_code(code, _FINGERPRINT)
        self.assertFalse(result["valid"])
        self.assertIn("指纹", result["reason"])

    def test_verify_expired_code(self):
        code = _make_code(_FINGERPRINT, (date.today() - timedelta(days=1)).strftime("%Y-%m-%d"))
        result = lic.verify_license_code(code, _FINGERPRINT)
        self.assertFalse(result["valid"])
        self.assertIn("过期", result["reason"])

    def test_verify_tampered_signature(self):
        code = _make_code(_FINGERPRINT, _future())
        payload_b64, sig_b64 = code.split(".", 1)
        tampered = payload_b64 + "." + sig_b64[:-2] + ("AA" if not sig_b64.endswith("AA") else "BB")
        result = lic.verify_license_code(tampered, _FINGERPRINT)
        self.assertFalse(result["valid"])

    def test_verify_malformed_code(self):
        self.assertFalse(lic.verify_license_code("not-a-code", _FINGERPRINT)["valid"])
        self.assertFalse(lic.verify_license_code("", _FINGERPRINT)["valid"])

    # ── 试用期与状态 ────────────────────────────────────────────
    def test_fresh_install_is_trial(self):
        status = lic.get_license_status()
        self.assertFalse(status["activated"])
        self.assertTrue(status["can_use"])
        self.assertTrue(status["trial"])
        self.assertEqual(status["trial_days_left"], lic.TRIAL_DAYS)
        self.assertEqual(status["fingerprint"], _FINGERPRINT)

    def test_trial_expired(self):
        from datetime import datetime
        old = (datetime.now() - timedelta(days=10)).replace(microsecond=0).isoformat()
        _reset_state(first_seen=old, last_seen=old)
        status = lic.get_license_status()
        self.assertFalse(status["can_use"])
        self.assertEqual(status["trial_days_left"], 0)

    def test_clock_rollback_uses_last_seen(self):
        from datetime import datetime
        now = datetime.now().replace(microsecond=0)
        first = now.isoformat()
        future_last = (now + timedelta(days=10)).isoformat()
        _reset_state(first_seen=first, last_seen=future_last)
        status = lic.get_license_status()
        # 有效当前时间被钳制到 last_seen(=now+10d)，已超出 3 天试用
        self.assertFalse(status["can_use"])

    def test_activate_then_activated(self):
        code = _make_code(_FINGERPRINT, _future())
        result = lic.activate_license(code)
        self.assertTrue(result["activated"], result.get("message"))

        status = lic.get_license_status()
        self.assertTrue(status["activated"])
        self.assertTrue(status["can_use"])
        self.assertFalse(status["trial"])

    def test_activate_invalid_code_rejected(self):
        result = lic.activate_license(_make_code("0" * 64, _future()))
        self.assertFalse(result["activated"])
        self.assertTrue(result.get("error"))


if __name__ == "__main__":
    unittest.main()
