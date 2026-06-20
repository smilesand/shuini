"""
重新同步内嵌授权公钥模块
==========================
从 ``scripts/keys/private_key.pem`` 派生公钥，重新生成内嵌公钥模块
``backend/core/_license_pubkey.py``（XOR 混淆 + SHA-256 完整性校验）。

通常无需单独运行——``scripts/init_license_keys.py`` 已包含该步骤；当你只想在不重建
密钥的情况下刷新内嵌公钥模块时使用本脚本。

用法::

    python scripts/extract_public_key.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from init_license_keys import (  # noqa: E402
    PRIVATE_KEY_PATH,
    PUBKEY_MODULE_PATH,
    sync_public_module,
)


def main() -> None:
    if not PRIVATE_KEY_PATH.is_file():
        print(f"❌ 未找到私钥源: {PRIVATE_KEY_PATH}（请先运行 scripts/init_license_keys.py）")
        raise SystemExit(1)
    sync_public_module()
    print(f"✅ 已重新生成内嵌公钥模块: {PUBKEY_MODULE_PATH}")


if __name__ == "__main__":
    main()
