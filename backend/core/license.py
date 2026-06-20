"""
单机版授权核心
================
提供机器指纹计算、授权码（RSA-PSS 签名）校验、试用期与激活状态管理。

授权码格式（与 release/license-tool/wtcmd-license-tool.py 一致）::

    base64url(payload_json) + "." + base64url(signature)

其中 ``payload_json`` 为 ``json.dumps({"v":1,"fp":<FP>,"exp":"YYYY-MM-DD"},
ensure_ascii=False, sort_keys=True)``，签名为 RSA-PSS(MGF1-SHA256, max salt)
覆盖 ``payload_json`` 的 UTF-8 字节。

仅桌面/单机版（``SC_EDITION=desktop``）启用试用期与激活强制；其他形态默认放行。
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import sys
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from core.config import get_settings

logger = logging.getLogger("wtcmd.license")

TRIAL_DAYS = 3


# ──────────────────────────────────────────────────────────────────────────
# 机器指纹
# ──────────────────────────────────────────────────────────────────────────
def _windows_machine_guid() -> str:
    """读取 Windows 注册表中的 MachineGuid（跨重装相对稳定）。"""
    if sys.platform != "win32":
        return ""
    try:
        import winreg  # type: ignore

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        ) as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(value).strip()
    except OSError:
        return ""


def _mac_address() -> str:
    node = uuid.getnode()
    # uuid.getnode 在无法获取真实 MAC 时会返回随机值（第 8 位为 1），此时不参与指纹。
    if (node >> 40) & 0x1:
        return ""
    return f"{node:012x}"


def compute_fingerprint() -> str:
    """计算稳定的机器指纹（大写十六进制 SHA-256）。

    允许通过环境变量 ``SC_LICENSE_FINGERPRINT`` 覆盖，便于测试与离线签发。
    """
    override = os.getenv("SC_LICENSE_FINGERPRINT")
    if override:
        return override.strip().upper()

    parts = [
        _windows_machine_guid(),
        _mac_address(),
        sys.platform,
    ]
    seed = "|".join(p for p in parts if p)
    if not seed:
        # 极端兜底：使用主机名，保证至少返回一个稳定值。
        seed = os.getenv("COMPUTERNAME") or os.getenv("HOSTNAME") or "unknown-host"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest().upper()
    return digest


# ──────────────────────────────────────────────────────────────────────────
# 公钥加载与授权码校验
# ──────────────────────────────────────────────────────────────────────────
def _load_embedded_public_key_pem() -> Optional[str]:
    """从编译进程序内部的内嵌公钥模块解码并校验公钥 PEM。

    内嵌公钥经 XOR 混淆 + SHA-256 完整性校验，任何人为替换都会校验失败被拒绝。
    模块由 ``scripts/init_license_keys.py`` 生成。
    """
    try:
        from core import _license_pubkey  # 延迟导入：未生成时不影响其它逻辑
    except ImportError:
        logger.error(
            "未找到内嵌授权公钥模块 core._license_pubkey；"
            "请运行 scripts/init_license_keys.py 生成"
        )
        return None
    try:
        return _license_pubkey.load_public_key_pem()
    except Exception:  # noqa: BLE001 - 校验失败/损坏时返回 None
        logger.exception("内嵌授权公钥校验失败（疑似被篡改）")
        return None


def _load_public_key():
    # 仅开发/测试态（未打包）允许用环境变量注入公钥，便于单元测试；
    # 打包发布后(frozen)只信任编译进程序的内嵌公钥，杜绝文件/环境变量替换。
    pem: Optional[str] = None
    if not getattr(sys, "frozen", False):
        pem = os.getenv("SC_LICENSE_PUBLIC_KEY_PEM")
    if not pem:
        pem = _load_embedded_public_key_pem()
    if not pem:
        return None
    try:
        from cryptography.hazmat.primitives.serialization import load_pem_public_key

        return load_pem_public_key(pem.encode("utf-8"))
    except Exception:  # noqa: BLE001 - 公钥损坏时返回 None，由上层处理
        logger.exception("加载授权公钥失败")
        return None


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def verify_license_code(code: str, fingerprint: str) -> dict:
    """校验授权码。

    返回 ``{"valid": bool, "reason": str, "expiry": Optional[str]}``。
    ``reason`` 在失败时给出原因，成功时为 ``"ok"``。
    """
    code = (code or "").strip()
    if not code or "." not in code:
        return {"valid": False, "reason": "授权码格式无效", "expiry": None}

    public_key = _load_public_key()
    if public_key is None:
        return {"valid": False, "reason": "缺少授权公钥，无法校验", "expiry": None}

    try:
        payload_b64, sig_b64 = code.split(".", 1)
        payload_bytes = _b64url_decode(payload_b64)
        signature = _b64url_decode(sig_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return {"valid": False, "reason": "授权码解析失败", "expiry": None}

    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.exceptions import InvalidSignature

        public_key.verify(
            signature,
            payload_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
    except InvalidSignature:
        return {"valid": False, "reason": "授权码签名无效", "expiry": None}
    except Exception:  # noqa: BLE001
        logger.exception("授权码校验异常")
        return {"valid": False, "reason": "授权码校验异常", "expiry": None}

    fp_in_code = str(payload.get("fp", "")).upper()
    if fp_in_code != fingerprint.upper():
        return {"valid": False, "reason": "授权码与本机指纹不匹配", "expiry": None}

    expiry = str(payload.get("exp", "")).strip()
    try:
        expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
    except ValueError:
        return {"valid": False, "reason": "授权码到期日期无效", "expiry": None}

    if expiry_date < date.today():
        return {"valid": False, "reason": "授权码已过期", "expiry": expiry}

    return {"valid": True, "reason": "ok", "expiry": expiry}


# ──────────────────────────────────────────────────────────────────────────
# 状态存储（license_state 单行表）与试用期
# ──────────────────────────────────────────────────────────────────────────
def _now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _load_state(conn) -> dict:
    row = conn.execute(
        "SELECT fingerprint, license_code, expiry, activated_at, first_seen, last_seen "
        "FROM license_state WHERE id=1"
    ).fetchone()
    if row is None:
        now = _now_iso()
        fingerprint = compute_fingerprint()
        conn.execute(
            "INSERT INTO license_state (id, fingerprint, license_code, expiry, "
            "activated_at, first_seen, last_seen) VALUES (1, ?, NULL, NULL, NULL, ?, ?)",
            (fingerprint, now, now),
        )
        conn.commit()
        return {
            "fingerprint": fingerprint,
            "license_code": None,
            "expiry": None,
            "activated_at": None,
            "first_seen": now,
            "last_seen": now,
        }
    return dict(row)


def _touch_last_seen(conn, state: dict) -> datetime:
    """更新 last_seen，返回用于试用计算的"有效当前时间"（防时钟回拨）。"""
    now = datetime.now().replace(microsecond=0)
    last_seen = _parse_iso(state.get("last_seen")) or now
    effective_now = max(now, last_seen)
    if effective_now > last_seen:
        conn.execute(
            "UPDATE license_state SET last_seen=? WHERE id=1",
            (effective_now.isoformat(),),
        )
        conn.commit()
    return effective_now


def _trial_days_left(state: dict, effective_now: datetime) -> int:
    first_seen = _parse_iso(state.get("first_seen")) or effective_now
    trial_end = first_seen + timedelta(days=TRIAL_DAYS)
    remaining = trial_end - effective_now
    if remaining.total_seconds() <= 0:
        return 0
    # 向上取整为天数
    return max(0, (remaining.days + (1 if remaining.seconds or remaining.microseconds else 0)))


def get_license_status() -> dict:
    """返回授权状态字典，供 /api/license/status 使用。"""
    settings = get_settings()
    fingerprint = compute_fingerprint()

    # 非桌面形态不强制授权。
    if settings.edition != "desktop":
        return {
            "edition": settings.edition,
            "fingerprint": fingerprint,
            "activated": True,
            "can_use": True,
            "expiry": None,
            "trial": False,
            "trial_days_left": None,
            "message": "当前部署无需激活",
        }

    from database import get_db

    conn = get_db()
    try:
        state = _load_state(conn)
        effective_now = _touch_last_seen(conn, state)

        code = state.get("license_code")
        if code:
            result = verify_license_code(code, fingerprint)
            if result["valid"]:
                return {
                    "edition": settings.edition,
                    "fingerprint": fingerprint,
                    "activated": True,
                    "can_use": True,
                    "expiry": result["expiry"],
                    "trial": False,
                    "trial_days_left": None,
                    "message": "已激活",
                }
            # 已存授权码但失效（过期/换硬件）→ 回退到试用判断。
            logger.warning("已存储授权码校验失败: %s", result["reason"])

        days_left = _trial_days_left(state, effective_now)
        can_use = days_left > 0
        return {
            "edition": settings.edition,
            "fingerprint": fingerprint,
            "activated": False,
            "can_use": can_use,
            "expiry": None,
            "trial": True,
            "trial_days_left": days_left,
            "message": (f"试用中，剩余 {days_left} 天" if can_use else "试用期已结束，请激活后继续使用"),
        }
    finally:
        conn.close()


def activate_license(license_code: str) -> dict:
    """校验并保存授权码。返回 ``{"activated": bool, "message": str, ...}``。"""
    settings = get_settings()
    fingerprint = compute_fingerprint()

    if settings.edition != "desktop":
        return {
            "activated": True,
            "can_use": True,
            "fingerprint": fingerprint,
            "expiry": None,
            "message": "当前部署无需激活",
        }

    result = verify_license_code(license_code, fingerprint)
    if not result["valid"]:
        return {
            "activated": False,
            "can_use": False,
            "fingerprint": fingerprint,
            "expiry": None,
            "message": result["reason"],
            "error": True,
        }

    from database import get_db

    conn = get_db()
    try:
        _load_state(conn)  # 确保行存在
        conn.execute(
            "UPDATE license_state SET license_code=?, expiry=?, activated_at=?, fingerprint=? "
            "WHERE id=1",
            (license_code.strip(), result["expiry"], _now_iso(), fingerprint),
        )
        conn.commit()
    finally:
        conn.close()

    logger.info("授权激活成功 fp=%s exp=%s", fingerprint, result["expiry"])
    return {
        "activated": True,
        "can_use": True,
        "fingerprint": fingerprint,
        "expiry": result["expiry"],
        "message": "激活成功",
    }
