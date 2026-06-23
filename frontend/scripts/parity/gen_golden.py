"""
parity/gen_golden.py
====================
读取共享测试夹具 fixtures.json，调用「服务端计算函数」（迁移前的事实标准）
为每个夹具生成期望输出，写入 golden.json。

随后由 parity.ts 用「前端计算引擎」对同一批夹具求值并逐字段比对，
以验证前端 src/calc 引擎与后端 services 的计算口径完全一致。

用法（从仓库任意位置）：
    python frontend/scripts/parity/gen_golden.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]  # frontend/scripts/parity -> 仓库根
BACKEND_DIR = REPO_ROOT / "backend"

# 让 `services` 包可被导入
sys.path.insert(0, str(BACKEND_DIR))

from services.calculations import (  # noqa: E402
    calc_water_binder,
    fit_regression_coefficients,
    calc_aggregate,
    calc_binder,
    calc_water_admixture,
    calc_uhpc_mix,
    calc_hpc_trial,
    calc_uhpc_trial,
)
from services.adapt import calc_adapt  # noqa: E402


def main() -> None:
    fixtures = json.loads((HERE / "fixtures.json").read_text(encoding="utf-8"))
    golden: dict[str, list[dict]] = {}

    def run(section: str, fn) -> None:
        golden[section] = []
        for case in fixtures.get(section, []):
            result = fn(case["input"])
            golden[section].append({"name": case["name"], "expected": result})

    run("water_binder", lambda i: calc_water_binder(**i))
    run("aggregate", lambda i: calc_aggregate(**i))
    run("binder", lambda i: calc_binder(**i))
    run("water_admixture", lambda i: calc_water_admixture(**i))
    run("regression", lambda i: fit_regression_coefficients(i["csv_text"]))
    run("adapt", lambda i: calc_adapt(**i))
    run("hpc_trial", lambda i: calc_hpc_trial(**i))
    run("uhpc_mix", lambda i: calc_uhpc_mix(**i))
    run("uhpc_trial", lambda i: calc_uhpc_trial(**i))

    out = HERE / "golden.json"
    out.write_text(json.dumps(golden, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(v) for v in golden.values())
    print(f"[gen_golden] wrote {total} expected cases across {len(golden)} sections -> {out}")


if __name__ == "__main__":
    main()
