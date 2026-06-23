"""
Excel 导入与校验服务
===================
解析上传的 .xlsx 文件（横排分节版面，与 PDF/导出一致）。

版面采用「表头行 + 数值行」的横排结构，导入只需填写
「配合比关键参数（填写区）」中的少量关键参数：
  HPC : 强度等级、水胶比、砂率、Vg、外加剂掺量
  UHPC: 强度等级、水胶比、胶砂比、钢纤维体积掺量、外加剂掺量
其余派生/计算字段允许缺省，由前端按默认值补全，校验从宽处理。
"""

from __future__ import annotations

import io
import re
from typing import Any

from openpyxl import load_workbook
from services.water_binder import calculate_water_binder_ratio, calculate_fcu0

# 校验容差
WB_TOLERANCE = 0.01      # 水胶比容差

# 配比计算合理范围（导入范围校验：值缺省不校验，超范围视为不合格）
SLUMP_RANGE = (10.0, 300.0)     # 坍落度 mm
SPREAD_RANGE = (200.0, 900.0)   # 扩展度 mm
AGG_SIZE_RANGE = (5.0, 40.0)    # 粗骨料最大粒径 mm


def _item(param: str, actual: Any, *, expected: Any = None, diff: Any = None,
          tolerance: Any = None, passed: bool = True) -> dict[str, Any]:
    """构造统一结构的校验项，确保前端所需字段齐全。"""
    return {
        "param": param,
        "expected": expected,
        "actual": actual,
        "diff": diff,
        "passed": passed,
        "tolerance": tolerance,
    }


def _num_from(raw: Any) -> float | None:
    """从可能带单位的文本/数值中解析首个数值（如 "20.0 mm" -> 20.0）。"""
    val = _parse_float(raw)
    if val is not None:
        return val
    if raw is None:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", str(raw))
    return float(match.group()) if match else None


def _fmt_num(value: float) -> str:
    """去除多余小数（5.0 -> 5）。"""
    return str(int(value)) if float(value).is_integer() else str(value)


def _range_check(param: str, raw: Any, lo: float, hi: float, unit: str,
                 items: list[dict[str, Any]], warnings: list[str]) -> bool:
    """范围校验：值缺省 -> 不生成校验项并视为合格；超范围 -> 生成不合格项 + 警告。

    返回 True 表示合格（或缺省），False 表示超出范围。
    """
    val = _num_from(raw)
    if val is None:
        return True
    range_text = f"{_fmt_num(lo)}~{_fmt_num(hi)} {unit}"
    ok = lo <= val <= hi
    items.append(_item(f"{param}范围", _round(val, 1), tolerance=range_text, passed=ok))
    if not ok:
        warnings.append(f"{param} {_fmt_num(val)} {unit} 超出合理范围（{range_text}）")
    return ok


# ── 横排表头映射：表头标签 → 内部字段名（可多键）──────────────────────────────
_HEADER_MAP: dict[str, list[str]] = {
    "强度等级/mpa": ["fcuk", "strength_grade"],
    "扩展度/mm": ["req_spread"],
    "坍落度/mm": ["req_slump"],
    "胶材28d强度/mpa": ["fb"],
    "粗骨料最大粒径/mm": ["max_aggregate_size"],
    "水胶比 w/b": ["wb", "water_binder_ratio"],
    "砂率 βs/%": ["sand_ratio"],
    "粗骨料体积 vg/m³": ["vg"],
    "外加剂掺量 α/%": ["alpha", "admixture_ratio"],
    "胶砂比": ["sand_binder_ratio"],
    "钢纤维体积掺量/%": ["steel_fiber_volume_ratio"],
}

# 同行 标签|值 映射（值在标签右侧单元格）
_INLINE_MAP: dict[str, str] = {
    "配比类别": "category",
    "记录名称": "record_name",
}


def _parse_float(value: Any) -> float | None:
    """尝试将值转为 float，失败返回 None。"""
    if value is None:
        return None
    if isinstance(value, bool):
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


def _store(result: dict[str, Any], keys: list[str], raw: Any) -> None:
    """按 keys 存值（数值优先；首次出现的有效值生效）。"""
    parsed = _parse_float(raw)
    if parsed is not None:
        for k in keys:
            result.setdefault(k, parsed)
        return
    if raw is not None and str(raw).strip():
        text = str(raw).strip()
        for k in keys:
            result.setdefault(k, text)


def parse_template_sheet(worksheet) -> dict[str, Any]:
    """
    解析横排分节模板 sheet。

    - 同行 标签|值：识别「配比类别」「记录名称」等内联键。
    - 表头行 + 数值行：表头标签命中映射时，读取下一行同列的数值。
    返回 { key: value } 字典。
    """
    rows: list[list[Any]] = [list(r) for r in worksheet.iter_rows(values_only=True)]
    result: dict[str, Any] = {}
    n = len(rows)

    for i, row in enumerate(rows):
        for c, cell in enumerate(row):
            if cell is None:
                continue
            label = str(cell).strip()
            if not label:
                continue
            norm = label.lower()

            # 内联 标签|值（同行右侧）
            inline_key = _INLINE_MAP.get(label)
            if inline_key is not None:
                value = row[c + 1] if c + 1 < len(row) else None
                if inline_key == "category":
                    if value is not None and str(value).strip():
                        result.setdefault("category", str(value).strip().lower())
                else:
                    _store(result, [inline_key], value)
                continue

            # 表头行 → 下一行同列取值（若紧邻行为空，回退取再下一行，兼容两级表头）
            keys = _HEADER_MAP.get(norm)
            if keys:
                value: Any = None
                for offset in (1, 2):
                    if i + offset >= n:
                        break
                    value_row = rows[i + offset]
                    candidate = value_row[c] if c < len(value_row) else None
                    if candidate is not None and str(candidate).strip():
                        value = candidate
                        break
                _store(result, keys, value)

    return result


def validate_hpc(data: dict[str, Any]) -> dict[str, Any]:
    """
    HPC 导入校验（从宽）。
    只要核心关键参数（强度等级、水胶比、砂率）齐备即视为有效；
    其余派生参数缺省不阻断导入。若提供了胶材强度 fb，则对水胶比做一致性提示（不阻断）。
    """
    items: list[dict[str, Any]] = []
    warnings: list[str] = []

    fcuk = data.get("fcuk")
    fb = data.get("fb")
    wb = data.get("wb")
    sand_ratio = data.get("sand_ratio")
    vg = data.get("vg")
    alpha = data.get("alpha")

    if fcuk is not None:
        items.append(_item("强度等级", _round(fcuk, 1)))
    else:
        warnings.append("缺少强度等级（fcu,k）")

    if wb is not None:
        expected = None
        diff = None
        # 若可重算，给出参考期望值（仅提示，不阻断）
        if fcuk is not None and fb is not None:
            aa = data.get("aa", 0.33)
            ab = data.get("ab", 1.09)
            ac = data.get("ac", -49.54)
            try:
                ev = calculate_water_binder_ratio(calculate_fcu0(fcuk), fb, aa, ab, ac)
                expected = round(ev, 4)
                diff = round(abs(ev - float(wb)), 4)
                if diff > WB_TOLERANCE:
                    warnings.append(f"水胶比与按 fcu,k/fb 重算值相差 {diff}（仅提示）")
            except (ValueError, TypeError):
                pass
        items.append(_item("水胶比", _round(wb, 4), expected=expected, diff=diff, tolerance=WB_TOLERANCE))
    else:
        warnings.append("缺少水胶比（W/B）")

    if sand_ratio is not None:
        items.append(_item("砂率", _round(sand_ratio, 2)))
    else:
        warnings.append("缺少砂率（βs）")

    if vg is not None:
        items.append(_item("粗骨料体积 Vg", _round(vg, 4)))
    if alpha is not None:
        items.append(_item("外加剂掺量", _round(alpha, 2)))

    # 范围校验：坍落度 / 扩展度 / 粗骨料最大粒径
    range_ok = True
    range_ok &= _range_check("坍落度", data.get("req_slump"), *SLUMP_RANGE, "mm", items, warnings)
    range_ok &= _range_check("扩展度", data.get("req_spread"), *SPREAD_RANGE, "mm", items, warnings)
    range_ok &= _range_check("粗骨料最大粒径", data.get("max_aggregate_size"), *AGG_SIZE_RANGE, "mm", items, warnings)

    valid = (fcuk is not None and wb is not None and sand_ratio is not None) and range_ok
    return {"valid": valid, "items": items, "warnings": warnings}


def validate_uhpc(data: dict[str, Any]) -> dict[str, Any]:
    """UHPC 导入校验（从宽）。强度等级 + 水胶比齐备即有效。"""
    items: list[dict[str, Any]] = []
    warnings: list[str] = []

    grade = data.get("strength_grade") or data.get("fcuk")
    wb = data.get("water_binder_ratio") or data.get("wb")
    sb = data.get("sand_binder_ratio")
    sf = data.get("steel_fiber_volume_ratio")
    alpha = data.get("admixture_ratio") or data.get("alpha")

    if grade is not None:
        items.append(_item("强度等级", _round(grade, 0)))
    else:
        warnings.append("缺少强度等级")
    if wb is not None:
        items.append(_item("水胶比", _round(wb, 4), tolerance=WB_TOLERANCE))
    else:
        warnings.append("缺少水胶比")
    if sb is not None:
        items.append(_item("胶砂比", _round(sb, 4)))
    if sf is not None:
        items.append(_item("钢纤维体积掺量", _round(sf, 2)))
    if alpha is not None:
        items.append(_item("外加剂掺量", _round(alpha, 2)))

    # 范围校验：坍落度 / 扩展度
    range_ok = True
    range_ok &= _range_check("坍落度", data.get("req_slump"), *SLUMP_RANGE, "mm", items, warnings)
    range_ok &= _range_check("扩展度", data.get("req_spread"), *SPREAD_RANGE, "mm", items, warnings)

    valid = (grade is not None and wb is not None) and range_ok
    return {"valid": valid, "items": items, "warnings": warnings}


def _round(value: Any, digits: int) -> Any:
    try:
        return round(float(value), digits)
    except (ValueError, TypeError):
        return value


def _detect_category(data: dict[str, Any]) -> str:
    category = data.get("category", "hpc")
    if isinstance(category, str):
        category = category.lower().strip()
    if category not in ("hpc", "uhpc"):
        category = "hpc"
    return category


def parse_and_validate_excel(file_bytes: bytes, filename: str = "") -> dict[str, Any]:
    """
    解析上传的 Excel 文件并执行校验（单条记录横排模板格式）。

    返回: {
        "category": "hpc" | "uhpc",
        "data": {...},
        "validation": { "valid": bool, "items": [...], "warnings": [...] },
    }
    """
    wb = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
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

    category = _detect_category(data)
    data["category"] = category
    validation = validate_uhpc(data) if category == "uhpc" else validate_hpc(data)

    return {
        "category": category,
        "data": data,
        "validation": validation,
    }


# ── 项目导入（多 sheet）──────────────────────────────────────────────────────

PROJECT_INFO_LABEL_MAP = {
    "项目编号": "project_code",
    "项目名称": "project_name",
    "技术要求": "requirements",
    "创建人": "created_by",
    "创建时间": "created_at",
    "导出时间": "exported_at",
    "记录数量": "record_count",
}


def parse_project_info_sheet(worksheet) -> dict[str, Any]:
    """解析「项目信息」sheet（简单 key-value 两列布局）。"""
    result: dict[str, Any] = {}
    for row in worksheet.iter_rows(min_row=1, max_col=2, values_only=True):
        if not row or not row[0]:
            continue
        label = str(row[0]).strip()
        value = row[1] if len(row) > 1 else None
        key = PROJECT_INFO_LABEL_MAP.get(label)
        if key:
            result[key] = str(value).strip() if value is not None else ""
    return result


def parse_project_import_excel(file_bytes: bytes) -> dict[str, Any]:
    """
    解析项目导入 Excel（多 sheet 格式，与项目导出对应）。

    Sheet 1 「项目信息」— 项目元数据
    后续 sheet — 各条记录（横排模板格式）
    """
    wb = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    sheet_names = wb.sheetnames

    if len(sheet_names) < 1:
        wb.close()
        raise ValueError("Excel 文件中没有 sheet")

    project_info = parse_project_info_sheet(wb[sheet_names[0]])

    records: list[dict[str, Any]] = []
    all_valid = True

    for sheet_name in sheet_names[1:]:
        ws = wb[sheet_name]
        data = parse_template_sheet(ws)
        if not data:
            continue

        category = _detect_category(data)
        data["category"] = category
        validation = validate_uhpc(data) if category == "uhpc" else validate_hpc(data)

        name = data.get("record_name") or sheet_name
        if not validation.get("valid"):
            all_valid = False

        records.append({
            "category": category,
            "name": str(name),
            "data": data,
            "validation": validation,
        })

    wb.close()

    return {
        "project": project_info,
        "records": records,
        "all_valid": all_valid,
    }
