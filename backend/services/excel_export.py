"""
Excel 导出服务
=============
生成配比导入模板、单条记录导出、项目导出（多 sheet）。
使用 openpyxl 生成 .xlsx 文件。
"""

from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

# ── 样式常量 ──────────────────────────────────────────────────────────────────
HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_FONT = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
SECTION_FILL = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")
SECTION_FONT = Font(name="微软雅黑", size=11, bold=True, color="1F4E79")
VALUE_FONT = Font(name="微软雅黑", size=10)
LABEL_FONT = Font(name="微软雅黑", size=10, bold=True)
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)
CENTER_ALIGN = Alignment(horizontal="center", vertical="center")
LEFT_ALIGN = Alignment(horizontal="left", vertical="center", wrap_text=True)

# ── 字段定义 ──────────────────────────────────────────────────────────────────
# FieldDef: (label, key, unit, section, reference, choices)
# choices: None = 自由输入, list[str] = 下拉选项

HPC_FIELDS: list[tuple[str, str, str, str, str, list[str] | None]] = [
    # 基本信息
    ("记录名称", "record_name", "", "基本信息", "如：C50基准配比", None),
    ("配比类别", "category", "", "基本信息", "固定填写 hpc", ["hpc"]),
    # 水胶比计算
    ("强度等级 fcu,k (MPa)", "fcuk", "MPa", "水胶比计算", "如：30/35/40/45/50/55/60", None),
    ("胶材28d强度 fb (MPa)", "fb", "MPa", "水胶比计算", "如：42.5", None),
    ("fb 计算模式", "fbCalcMode", "", "水胶比计算", "input=直接输入, calc=由γ系数推算", ["input", "calc"]),
    ("水泥强度等级 fce,g (MPa)", "fceG", "MPa", "水胶比计算", "如：42.5 / 52.5", None),
    ("水泥富余系数 γc", "gammaC", "", "水胶比计算", "通常 1.08~1.12", None),
    ("粉煤灰影响系数 γf", "gammaF", "", "水胶比计算", "通常 0.75~1.00", None),
    ("矿粉影响系数 γs", "gammaS", "", "水胶比计算", "通常 0.95~1.00", None),
    ("微珠影响系数 γb", "gammaB", "", "水胶比计算", "通常 1.00", None),
    ("硅灰影响系数 γSF", "gammaSF", "", "水胶比计算", "通常 1.00", None),
    ("回归系数 αa", "aa", "", "水胶比计算", "默认 0.33（碎石）", None),
    ("回归系数 αb", "ab", "", "水胶比计算", "默认 1.09（碎石）", None),
    ("回归系数 αc", "ac", "", "水胶比计算", "默认 -49.54", None),
    ("配制强度 fcu,0 (MPa)", "fcu0", "MPa", "水胶比计算", "fcuk × 1.15（系统自动计算）", None),
    ("水胶比 W/B", "wb", "", "水胶比计算", "αa×fb / (fcu0 + αa×αb×fb + αc)", None),
    # 砂率与骨料
    ("Vg 参考工作性等级", "vg_reference_code", "", "砂率与骨料", "SF0/SF1/SF2/SF3（坍落度/扩展度等级）", ["SF0", "SF1", "SF2", "SF3"]),
    ("粗骨料绝对体积 Vg (m³)", "vg", "m³", "砂率与骨料", "如：0.38（参考 SF1: 0.35~0.38）", None),
    ("粗骨料密度 ρg (kg/m³)", "rhog", "kg/m³", "砂率与骨料", "如：2700", None),
    ("细骨料密度 ρs (kg/m³)", "rhos", "kg/m³", "砂率与骨料", "如：2650", None),
    ("砂率 βs (%)", "sand_ratio", "%", "砂率与骨料", "如：35（表示35%）", None),
    ("粗骨料用量 mg (kg)", "mg", "kg", "砂率与骨料", "Vg × ρg（系统自动计算）", None),
    ("细骨料用量 ms (kg)", "ms", "kg", "砂率与骨料", "βs/(1-βs) × mg（系统自动计算）", None),
    # 胶凝材料
    ("粉煤灰掺量 β1 (%)", "b1p", "%", "胶凝材料", "如：20（表示20%）", None),
    ("粉煤灰密度 ρ1 (kg/m³)", "rho1", "kg/m³", "胶凝材料", "如：2200", None),
    ("矿粉掺量 β2 (%)", "b2p", "%", "胶凝材料", "如：15", None),
    ("矿粉密度 ρ2 (kg/m³)", "rho2", "kg/m³", "胶凝材料", "如：2900", None),
    ("微珠掺量 β3 (%)", "b3p", "%", "胶凝材料", "如：10", None),
    ("微珠密度 ρ3 (kg/m³)", "rho3", "kg/m³", "胶凝材料", "如：2600", None),
    ("硅灰掺量 β4 (%)", "b4p", "%", "胶凝材料", "如：5", None),
    ("硅灰密度 ρ4 (kg/m³)", "rho4", "kg/m³", "胶凝材料", "如：2200", None),
    ("水泥密度 ρc (kg/m³)", "rhoc", "kg/m³", "胶凝材料", "如：3100", None),
    ("含气量 Va", "va", "", "胶凝材料", "通常 0.01~0.02（不掺引气剂取 0.01）", None),
    ("水泥质量分数 βc", "bc", "", "胶凝材料", "1 - Σβi（系统自动计算）", None),
    ("胶材密度 ρb (kg/m³)", "rhob", "kg/m³", "胶凝材料", "1/Σ(βi/ρi)（系统自动计算）", None),
    ("浆体体积 Vp (m³)", "vp", "m³", "胶凝材料", "1 - mg/ρg - ms/ρs（系统自动计算）", None),
    ("胶凝材料总量 mb (kg)", "mb", "kg", "胶凝材料", "(Vp-Va) / (1/ρb + W/B)（系统自动计算）", None),
    ("粉煤灰用量 m1 (kg)", "m1", "kg", "胶凝材料", "mb × β1（系统自动计算）", None),
    ("矿粉用量 m2 (kg)", "m2", "kg", "胶凝材料", "mb × β2（系统自动计算）", None),
    ("微珠用量 m3 (kg)", "m3", "kg", "胶凝材料", "mb × β3（系统自动计算）", None),
    ("硅灰用量 m4 (kg)", "m4", "kg", "胶凝材料", "mb × β4（系统自动计算）", None),
    ("水泥用量 mc (kg)", "mc", "kg", "胶凝材料", "mb × βc（系统自动计算）", None),
    # 水和外加剂
    ("外加剂掺量 α (%)", "alpha", "%", "水和外加剂", "如：1.5（表示1.5%）", None),
    ("用水量 mw (kg)", "mw", "kg", "水和外加剂", "mb × W/B（系统自动计算）", None),
    ("外加剂用量 ma (kg)", "ma", "kg", "水和外加剂", "mb × α（系统自动计算）", None),
    ("每方总质量 (kg)", "total_mass", "kg", "水和外加剂", "mb + mg + ms + mw + ma（系统自动计算）", None),
]

UHPC_FIELDS: list[tuple[str, str, str, str, str, list[str] | None]] = [
    # 基本信息
    ("记录名称", "record_name", "", "基本信息", "如：UHPC130配比", None),
    ("配比类别", "category", "", "基本信息", "固定填写 uhpc", ["uhpc"]),
    # UHPC 配比参数
    ("强度等级 (MPa)", "strength_grade", "MPa", "UHPC配比参数", "如：120/130/140/150", None),
    ("水胶比 W/B", "water_binder_ratio", "", "UHPC配比参数", "如：0.19（通常 0.16~0.22）", None),
    ("外加剂掺量 α (%)", "admixture_ratio", "%", "UHPC配比参数", "如：1.8（表示1.8%）", None),
    ("胶砂比", "sand_binder_ratio", "", "UHPC配比参数", "如：1.20（通常 1.0~1.4）", None),
    ("钢纤维体积掺量 (%)", "steel_fiber_volume_ratio", "%", "UHPC配比参数", "如：1.8（通常 0~3%）", None),
    ("钢纤维强度等级", "fiber_strength_grade", "", "UHPC配比参数", "UT05(端钩型) / UT07(超细型)", ["UT05", "UT07"]),
    # 粒径分布
    ("体系最大粒径 (μm)", "max_particle_size", "μm", "粒径分布参数", "如：80", None),
    ("体系最小粒径 (μm)", "min_particle_size", "μm", "粒径分布参数", "如：1（通常 0.1~5）", None),
    ("粒径分布指数", "distribution_index", "", "粒径分布参数", "如：0.22（A&A模型 q 值）", None),
    ("粉煤灰峰值粒径 (μm)", "fly_ash_peak_size", "μm", "粒径分布参数", "如：18", None),
    ("粉煤灰堆积粒径 (μm)", "fly_ash_accumulation_size", "μm", "粒径分布参数", "如：8", None),
    ("微珠峰值粒径 (μm)", "micro_bead_peak_size", "μm", "粒径分布参数", "如：4", None),
    ("微珠占硅灰微粉比例", "micro_bead_silica_fume_ratio", "", "粒径分布参数", "如：0.50（0~1 之间）", None),
    # 密度参数
    ("水泥密度 (kg/m³)", "cement_density", "kg/m³", "密度参数", "如：3100", None),
    ("粉煤灰密度 (kg/m³)", "fly_ash_density", "kg/m³", "密度参数", "如：2300", None),
    ("微珠密度 (kg/m³)", "micro_bead_density", "kg/m³", "密度参数", "如：2600", None),
    ("硅灰密度 (kg/m³)", "silica_fume_density", "kg/m³", "密度参数", "如：2200", None),
    ("微粉系数", "micro_powder_coefficient", "", "密度参数", "如：0.55（>0）", None),
    ("假定拌合物质量 (kg)", "assumed_mix_mass", "kg", "密度参数", "如：2500", None),
    ("钢纤维密度 (kg/m³)", "steel_fiber_density", "kg/m³", "密度参数", "如：7850", None),
]


def _apply_cell_style(cell, font=None, fill=None, alignment=None, border=None):
    if font:
        cell.font = font
    if fill:
        cell.fill = fill
    if alignment:
        cell.alignment = alignment
    if border:
        cell.border = border


def _write_section_header(ws, row, col, section_name: str):
    """写入区块标题行（合并四列）。"""
    cell = ws.cell(row=row, column=col, value=section_name)
    _apply_cell_style(cell, font=SECTION_FONT, fill=SECTION_FILL,
                      alignment=CENTER_ALIGN, border=THIN_BORDER)
    ws.merge_cells(start_row=row, start_column=col, end_row=row, end_column=col + 3)
    for c in range(col, col + 4):
        _apply_cell_style(ws.cell(row=row, column=c), border=THIN_BORDER)


def _write_field_row(ws, row, col, label: str, value=None, unit: str = "", reference: str = "", choices: list[str] | None = None):
    """写入一行：标签 | 值 | 单位 | 参考数值。若 choices 非空则在值列设置下拉验证。"""
    label_cell = ws.cell(row=row, column=col, value=label)
    _apply_cell_style(label_cell, font=LABEL_FONT, border=THIN_BORDER, alignment=LEFT_ALIGN)
    value_cell = ws.cell(row=row, column=col + 1, value=value)
    _apply_cell_style(value_cell, font=VALUE_FONT, border=THIN_BORDER, alignment=CENTER_ALIGN)
    unit_cell = ws.cell(row=row, column=col + 2, value=unit)
    _apply_cell_style(unit_cell, font=VALUE_FONT, border=THIN_BORDER, alignment=CENTER_ALIGN)
    ref_cell = ws.cell(row=row, column=col + 3, value=reference)
    _apply_cell_style(ref_cell, font=VALUE_FONT, border=THIN_BORDER, alignment=LEFT_ALIGN)

    # 设置数据验证（下拉框）
    if choices:
        dv = DataValidation(
            type="list",
            formula1='"' + ','.join(choices) + '"',
            allow_blank=True,
        )
        dv.error = "请从下拉列表中选择"
        dv.errorTitle = "输入无效"
        ws.add_data_validation(dv)
        dv.add(value_cell)


def _write_header_row(ws, row, col):
    """写入表头行：参数名称 | 参数值 | 单位 | 参考数值。"""
    for i, title in enumerate(["参数名称", "参数值", "单位", "参考数值"]):
        cell = ws.cell(row=row, column=col + i, value=title)
        _apply_cell_style(cell, font=HEADER_FONT, fill=HEADER_FILL,
                          alignment=CENTER_ALIGN, border=THIN_BORDER)


# 兼容旧版 fields 类型的判断
def _is_new_field_format(field: tuple) -> bool:
    return len(field) >= 6


def _build_template_ws(ws, fields, data: dict[str, Any] | None = None):
    """在给定 worksheet 上按 fields 定义写入模板（含可选数据）。"""
    data = data or {}
    ws.sheet_properties.tabColor = "4472C4"
    col_widths = [32, 20, 8, 28]
    for i, w in enumerate(col_widths):
        ws.column_dimensions[get_column_letter(i + 1)].width = w

    row = 1
    _write_header_row(ws, row, 1)
    row += 1

    current_section = None
    for field in fields:
        if _is_new_field_format(field):
            label, key, unit, section, reference, choices = field
        else:
            # 兼容旧 4 元组格式
            label, key, unit, section = field[:4]
            reference = ""
            choices = None

        if section != current_section:
            current_section = section
            _write_section_header(ws, row, 1, section)
            row += 1

        value = data.get(key)
        if value is not None:
            if isinstance(value, float):
                value = round(value, 4)
            value = str(value)
        else:
            value = ""

        _write_field_row(ws, row, 1, label, value, unit, reference, choices)
        row += 1

    ws.auto_filter.ref = f"A1:D{row - 1}"
    ws.freeze_panes = "A3"


def generate_template_bytes(category: str) -> bytes:
    """生成空模板 Excel 的字节流。"""
    wb = Workbook()
    ws = wb.active
    ws.title = "配比导入模板"

    fields = HPC_FIELDS if category == "hpc" else UHPC_FIELDS
    _build_template_ws(ws, fields, {"category": category})

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def generate_record_export_bytes(record: dict[str, Any], project_name: str = "") -> bytes:
    """生成单条记录导出 Excel 的字节流。"""
    record_data = record.get("record_data", {}) or {}
    category = record.get("category", "hpc")
    name = record.get("name", "未命名")

    fields = HPC_FIELDS if category == "hpc" else UHPC_FIELDS

    # 对于 UHPC，数据在 design_data.inputs 中（camelCase），需转换为 UHPC_FIELDS 的 snake_case
    if category == "uhpc":
        export_data = {"category": "uhpc", "record_name": name}
        design_data = record_data.get("design_data", {}) or {}
        if isinstance(design_data, dict):
            inputs = design_data.get("inputs", {}) or {}
            if isinstance(inputs, dict):
                # 将 camelCase 的 inputs key 转换为 snake_case
                for camel_key, value in inputs.items():
                    snake_key = re.sub(r"(?<!^)(?=[A-Z])", "_", camel_key).lower()
                    export_data.setdefault(snake_key, value)
        # 补充 record_data 顶层字段（兼容旧数据格式）
        if "fcuk" in record_data:
            export_data.setdefault("strength_grade", record_data["fcuk"])
        if "wb" in record_data:
            export_data.setdefault("water_binder_ratio", record_data["wb"])
        if "alpha" in record_data:
            export_data.setdefault("admixture_ratio", record_data["alpha"])
        if "sand_ratio" in record_data:
            export_data.setdefault("sand_binder_ratio", record_data["sand_ratio"])
    else:
        export_data = dict(record_data)
        export_data["category"] = category
        export_data["record_name"] = name

    wb = Workbook()
    ws = wb.active
    ws.title = _safe_sheet_name(name)

    _build_template_ws(ws, fields, export_data)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def generate_project_export_bytes(project: dict[str, Any], records: list[dict[str, Any]]) -> bytes:
    """生成项目导出 Excel（多 sheet）的字节流。"""
    wb = Workbook()
    # Sheet 1: 项目信息
    ws_info = wb.active
    ws_info.title = "项目信息"
    ws_info.sheet_properties.tabColor = "4472C4"
    ws_info.column_dimensions["A"].width = 20
    ws_info.column_dimensions["B"].width = 40

    info_data = [
        ("项目编号", project.get("project_code", "")),
        ("项目名称", project.get("project_name", "")),
        ("技术要求", project.get("requirements", "")),
        ("创建人", project.get("created_by", "")),
        ("创建时间", project.get("created_at", "")),
        ("导出时间", datetime.now().strftime("%Y-%m-%d %H:%M")),
        ("记录数量", str(len(records))),
    ]
    for i, (label, value) in enumerate(info_data, start=1):
        label_cell = ws_info.cell(row=i, column=1, value=label)
        _apply_cell_style(label_cell, font=LABEL_FONT, border=THIN_BORDER, alignment=LEFT_ALIGN)
        value_cell = ws_info.cell(row=i, column=2, value=value)
        _apply_cell_style(value_cell, font=VALUE_FONT, border=THIN_BORDER, alignment=LEFT_ALIGN)

    # 每条记录一个 sheet
    for record in records:
        cat = record.get("category", "hpc")
        fields = HPC_FIELDS if cat == "hpc" else UHPC_FIELDS
        sheet_name = _safe_sheet_name(record.get("name", f"记录{record.get('id', '')}"))

        # 去重 sheet 名
        counter = 1
        base_name = sheet_name
        while sheet_name in wb.sheetnames:
            counter += 1
            sheet_name = f"{base_name[:28]}_{counter}"

        ws = wb.create_sheet(title=sheet_name)
        record_data = record.get("record_data", {}) or {}
        if cat == "uhpc":
            design_data = record_data.get("design_data", {}) or {}
            if isinstance(design_data, dict):
                inputs = design_data.get("inputs", {}) or {}
                # 将 camelCase 的 inputs key 转换为 snake_case（与 UHPC_FIELDS 一致）
                export_data: dict[str, Any] = {"category": "uhpc", "record_name": record.get("name", "")}
                if isinstance(inputs, dict):
                    for camel_key, value in inputs.items():
                        snake_key = re.sub(r"(?<!^)(?=[A-Z])", "_", camel_key).lower()
                        export_data.setdefault(snake_key, value)
                if "fcuk" in record_data:
                    export_data.setdefault("strength_grade", record_data["fcuk"])
                if "wb" in record_data:
                    export_data.setdefault("water_binder_ratio", record_data["wb"])
                if "alpha" in record_data:
                    export_data.setdefault("admixture_ratio", record_data["alpha"])
                if "sand_ratio" in record_data:
                    export_data.setdefault("sand_binder_ratio", record_data["sand_ratio"])
            else:
                export_data = {"category": "uhpc", "record_name": record.get("name", "")}
        else:
            export_data = dict(record_data)
            export_data["category"] = cat
            export_data["record_name"] = record.get("name", "")

        _build_template_ws(ws, fields, export_data)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def _safe_sheet_name(name: str, max_len: int = 31) -> str:
    """生成合法的 Excel sheet 名称。"""
    forbidden = r'[]:*?/\\'
    safe = "".join(c for c in name if c not in forbidden)
    safe = safe.strip("'")
    if not safe:
        safe = "Sheet"
    return safe[:max_len]


def _export_filename(prefix: str) -> str:
    """生成带时间戳的导出文件名。"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.xlsx"
