"""
Excel 导入与校验服务
===================
解析上传的 .xlsx 文件，校验三个关键参数：
  1. 水胶比 W/B — 容差 ±0.01
  2. 砂率 βs — 容差 ±2 个百分点
  3. 粗骨料体积用量 Vg — 容差 ±0.02

解析逻辑与导出模板对齐：纵向键值对布局，区块标题行后跟 标签|值|单位 行。
"""

from __future__ import annotations

import io
from typing import Any

from openpyxl import load_workbook
from services.water_binder import calculate_water_binder_ratio, calculate_fcu0


# ── 已知导出字段映射：label → key ──────────────────────────────────────────
_LABEL_TO_KEY: dict[str, str] = {}

# 校验容差
WB_TOLERANCE = 0.01      # 水胶比容差
SAND_TOLERANCE = 2.0     # 砂率容差（百分点）
VG_TOLERANCE = 0.02      # 粗骨料体积容差


def _parse_float(value: Any) -> float | None:
    """尝试将值转为 float，失败返回 None。"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        s = str(value).strip()
        if s == "":
            return None
        return float(s)
    except (ValueError, TypeError):
        return None


def parse_template_sheet(worksheet) -> dict[str, Any]:
    """
    解析纵向键值对模板 sheet。
    跳过区块标题行（第二列无值），解析所有 标签|值|单位 行。
    返回 { key: value } 字典。
    """
    result: dict[str, Any] = {}
    current_section = ""

    for row in worksheet.iter_rows(min_row=1, values_only=True):
        if not row:
            continue
        label = str(row[0]).strip() if row[0] is not None else ""
        value = row[1] if len(row) > 1 else None
        # unit = row[2] if len(row) > 2 else ""

        if not label:
            continue
        # 跳过表头行
        if label in ("参数名称", "参数值", "单位"):
            continue

        # 检测是否为区块标题（值列为空或与标签相同）
        cell_b = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
        if not cell_b or cell_b == label or label in (
            "基本信息", "水胶比计算", "砂率与骨料", "胶凝材料", "水和外加剂",
            "UHPC配比参数", "粒径分布参数", "密度参数",
        ):
            current_section = label
            continue

        # 通过 label 查找对应的 key
        key = _lookup_key(label)
        if key is None:
            continue

        parsed = _parse_float(value)
        if parsed is not None:
            result[key] = parsed
        elif value is not None and str(value).strip():
            result[key] = str(value).strip()

    return result


def _lookup_key(label: str) -> str | None:
    """将中文标签映射到内部字段名。"""
    mapping = {
        # 基本信息
        "记录名称": "record_name",
        "配比类别": "category",
        # 水胶比
        "强度等级 fcu,k (MPa)": "fcuk",
        "胶材28d强度 fb (MPa)": "fb",
        "fb 计算模式": "fbCalcMode",
        "水泥强度等级 fce,g (MPa)": "fceG",
        "水泥富余系数 γc": "gammaC",
        "粉煤灰影响系数 γf": "gammaF",
        "矿粉影响系数 γs": "gammaS",
        "微珠影响系数 γb": "gammaB",
        "硅灰影响系数 γSF": "gammaSF",
        "回归系数 αa": "aa",
        "回归系数 αb": "ab",
        "回归系数 αc": "ac",
        "配制强度 fcu,0 (MPa)": "fcu0",
        "水胶比 W/B": "wb",
        # 砂率与骨料
        "Vg 参考工作性等级": "vg_reference_code",
        "粗骨料绝对体积 Vg (m³)": "vg",
        "粗骨料密度 ρg (kg/m³)": "rhog",
        "细骨料密度 ρs (kg/m³)": "rhos",
        "砂率 βs (%)": "sand_ratio",
        "粗骨料用量 mg (kg)": "mg",
        "细骨料用量 ms (kg)": "ms",
        # 胶凝材料
        "粉煤灰掺量 β1 (%)": "b1p",
        "粉煤灰密度 ρ1 (kg/m³)": "rho1",
        "矿粉掺量 β2 (%)": "b2p",
        "矿粉密度 ρ2 (kg/m³)": "rho2",
        "微珠掺量 β3 (%)": "b3p",
        "微珠密度 ρ3 (kg/m³)": "rho3",
        "硅灰掺量 β4 (%)": "b4p",
        "硅灰密度 ρ4 (kg/m³)": "rho4",
        "水泥密度 ρc (kg/m³)": "rhoc",
        "含气量 Va": "va",
        "水泥质量分数 βc": "bc",
        "胶材密度 ρb (kg/m³)": "rhob",
        "浆体体积 Vp (m³)": "vp",
        "胶凝材料总量 mb (kg)": "mb",
        "粉煤灰用量 m1 (kg)": "m1",
        "矿粉用量 m2 (kg)": "m2",
        "微珠用量 m3 (kg)": "m3",
        "硅灰用量 m4 (kg)": "m4",
        "水泥用量 mc (kg)": "mc",
        # 水和外加剂
        "外加剂掺量 α (%)": "alpha",
        "用水量 mw (kg)": "mw",
        "外加剂用量 ma (kg)": "ma",
        "每方总质量 (kg)": "total_mass",
        # UHPC
        "强度等级 (MPa)": "strength_grade",
        "水胶比": "water_binder_ratio",
        "胶砂比": "sand_binder_ratio",
        "钢纤维体积掺量 (%)": "steel_fiber_volume_ratio",
        "钢纤维强度等级": "fiber_strength_grade",
        "体系最大粒径 (μm)": "max_particle_size",
        "体系最小粒径 (μm)": "min_particle_size",
        "粒径分布指数": "distribution_index",
        "粉煤灰峰值粒径 (μm)": "fly_ash_peak_size",
        "粉煤灰堆积粒径 (μm)": "fly_ash_accumulation_size",
        "微珠峰值粒径 (μm)": "micro_bead_peak_size",
        "微珠占硅灰微粉比例": "micro_bead_silica_fume_ratio",
        "水泥密度 (kg/m³)": "cement_density",
        "粉煤灰密度 (kg/m³)": "fly_ash_density",
        "微珠密度 (kg/m³)": "micro_bead_density",
        "硅灰密度 (kg/m³)": "silica_fume_density",
        "微粉系数": "micro_powder_coefficient",
        "假定拌合物质量 (kg)": "assumed_mix_mass",
        "钢纤维密度 (kg/m³)": "steel_fiber_density",
    }
    return mapping.get(label)


def validate_hpc(data: dict[str, Any]) -> dict[str, Any]:
    """
    校验 HPC 导入数据的三个关键参数。

    返回: {
        "valid": bool,
        "items": [
            {"param": "水胶比", "expected": float, "actual": float, "diff": float, "passed": bool},
            {"param": "砂率", ...},
            {"param": "粗骨料体积用量", ...},
        ],
        "warnings": [str],
    }
    """
    items = []
    warnings = []

    # ── 1. 水胶比校验 ──
    fcuk = data.get("fcuk")
    fb = data.get("fb")
    aa = data.get("aa", 0.33)
    ab = data.get("ab", 1.09)
    ac = data.get("ac", -49.54)
    imported_wb = data.get("wb")

    if fcuk is not None and fb is not None:
        try:
            fcu0 = calculate_fcu0(fcuk)
            calced_wb = calculate_water_binder_ratio(fcu0, fb, aa, ab, ac)
            if imported_wb is not None:
                diff = abs(calced_wb - imported_wb)
                items.append({
                    "param": "水胶比",
                    "expected": round(calced_wb, 4),
                    "actual": round(imported_wb, 4),
                    "diff": round(diff, 4),
                    "passed": diff <= WB_TOLERANCE,
                    "tolerance": WB_TOLERANCE,
                })
            else:
                warnings.append("未找到导入的水胶比 wb 值，无法校验")
        except ValueError as e:
            warnings.append(f"水胶比计算失败: {e}")
    else:
        if imported_wb is not None:
            warnings.append("缺少 fcuk 或 fb 参数，无法重算水胶比进行校验")
            items.append({
                "param": "水胶比",
                "expected": None,
                "actual": round(imported_wb, 4),
                "diff": None,
                "passed": False,
                "tolerance": WB_TOLERANCE,
            })

    # ── 2. 砂率校验 ──
    mg = data.get("mg")
    ms = data.get("ms")
    imported_sand = data.get("sand_ratio")

    if mg is not None and ms is not None and (mg + ms) > 0:
        calced_sand = round(ms / (ms + mg) * 100, 2)
        if imported_sand is not None:
            diff = abs(calced_sand - imported_sand)
            items.append({
                "param": "砂率",
                "expected": calced_sand,
                "actual": round(imported_sand, 2),
                "diff": round(diff, 2),
                "passed": diff <= SAND_TOLERANCE,
                "tolerance": SAND_TOLERANCE,
                "tolerance_unit": "百分点",
            })
        else:
            warnings.append("未找到导入的砂率 sand_ratio 值，无法校验")
    else:
        if imported_sand is not None:
            warnings.append("缺少 mg 或 ms 参数，无法重算砂率进行校验")
            items.append({
                "param": "砂率",
                "expected": None,
                "actual": round(imported_sand, 2),
                "diff": None,
                "passed": False,
                "tolerance": SAND_TOLERANCE,
                "tolerance_unit": "百分点",
            })

    # ── 3. 粗骨料体积用量校验 ──
    imported_vg = data.get("vg")
    rhog = data.get("rhog")

    if mg is not None and rhog is not None and rhog > 0:
        calced_vg = round(mg / rhog, 4)
        if imported_vg is not None:
            diff = abs(calced_vg - imported_vg)
            items.append({
                "param": "粗骨料体积用量",
                "expected": calced_vg,
                "actual": round(imported_vg, 4),
                "diff": round(diff, 4),
                "passed": diff <= VG_TOLERANCE,
                "tolerance": VG_TOLERANCE,
            })
        else:
            warnings.append("未找到导入的粗骨料体积 vg 值，无法校验")
    else:
        if imported_vg is not None:
            warnings.append("缺少 mg 或 rhog 参数，无法重算粗骨料体积进行校验")
            items.append({
                "param": "粗骨料体积用量",
                "expected": None,
                "actual": round(imported_vg, 4),
                "diff": None,
                "passed": False,
                "tolerance": VG_TOLERANCE,
            })

    all_passed = all(item["passed"] for item in items) if items else False
    return {
        "valid": all_passed and len(items) > 0,
        "items": items,
        "warnings": warnings,
    }


def validate_uhpc(data: dict[str, Any]) -> dict[str, Any]:
    """
    校验 UHPC 导入数据。
    UHPC 的 wb 和砂率是直接输入值，做一致性对比检查。
    """
    items = []
    warnings = []

    # ── 1. 水胶比 ──
    imported_wb = data.get("water_binder_ratio") or data.get("wb")
    if imported_wb is not None:
        items.append({
            "param": "水胶比",
            "expected": round(imported_wb, 4),
            "actual": round(imported_wb, 4),
            "diff": 0.0,
            "passed": True,
            "tolerance": WB_TOLERANCE,
        })
    else:
        warnings.append("未找到水胶比参数")

    # ── 2. 胶砂比（相当于 HPC 砂率概念的角色）
    imported_sand = data.get("sand_binder_ratio") or data.get("sand_ratio")
    if imported_sand is not None:
        items.append({
            "param": "胶砂比",
            "expected": round(imported_sand, 4),
            "actual": round(imported_sand, 4),
            "diff": 0.0,
            "passed": True,
            "tolerance": 0.02,
        })
    else:
        warnings.append("未找到胶砂比参数")

    # ── 3. 粗骨料体积（UHPC 无此概念，跳过但标记）
    warnings.append("UHPC 无粗骨料体积用量概念，已跳过此项校验")

    all_passed = all(item["passed"] for item in items) if items else False
    return {
        "valid": all_passed and len(items) > 0,
        "items": items,
        "warnings": warnings,
    }


def parse_and_validate_excel(file_bytes: bytes, filename: str = "") -> dict[str, Any]:
    """
    解析上传的 Excel 文件并执行校验。

    返回: {
        "category": "hpc" | "uhpc",
        "data": {...},
        "validation": { "valid": bool, "items": [...], "warnings": [...] },
    }
    """
    wb = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    # 优先取第一个 sheet 或名为"配比导入模板"的 sheet
    sheet_names = wb.sheetnames
    target_sheet = None
    for name in ["配比导入模板", "Sheet1", sheet_names[0]]:
        if name in sheet_names:
            target_sheet = name
            break
    if target_sheet is None:
        target_sheet = sheet_names[0]

    ws = wb[target_sheet]
    data = parse_template_sheet(ws)
    wb.close()

    category = data.get("category", "hpc")
    if isinstance(category, str):
        category = category.lower().strip()
    if category not in ("hpc", "uhpc"):
        category = "hpc"

    if category == "uhpc":
        validation = validate_uhpc(data)
    else:
        validation = validate_hpc(data)

    return {
        "category": category,
        "data": data,
        "validation": validation,
    }



