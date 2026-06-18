"""
高性能试配统一计算服务
====================
将工作性实验、强度实验、配合比校正与确认三步涉及的数值推导统一收敛到服务端，
前端仅保留输入采集、节流防抖触发和结果展示，避免同一套业务公式在前后端重复维护。

实现原则：
    1. 与迁移前前端公式保持一致，确保结果口径不变。
    2. 对用户编辑中的临界输入返回空结果，而不是直接抛异常，减少界面抖动。
    3. 内部统一使用接近前端 Math.round 的舍入方式，降低跨端舍入差异。
"""

from __future__ import annotations

import math
from typing import Optional


# 统一维护试配页展示的材料顺序，保证工作性、试拌量、校正结果使用同一列顺序。
TRIAL_MATERIALS: tuple[tuple[str, str], ...] = (
    ("mc", "水泥"),
    ("m1", "粉煤灰"),
    ("m2", "矿粉"),
    ("m3", "微珠"),
    ("m4", "硅灰"),
    ("mg", "粗骨料"),
    ("ms", "细骨料"),
    ("mw", "水"),
    ("ma", "外加剂"),
)

RECOMMEND_STRENGTH_MARGIN = 0.1
RECOMMEND_WB_DIGITS = 2


def _round_js(value: float, digits: int = 4) -> float:
    """
    使用与前端 Math.round 接近的舍入策略。

    迁移前前端使用 `Math.round(value * factor) / factor`，这里用 floor(x + 0.5)
    近似同样的正负数舍入规则，尽量避免 Python 内置 round 的银行家舍入导致跨端差异。
        4. 外加剂掺量由用户在强度试验页输入（trial_alpha）；未输入时沿用工作性的 alpha。
    """
    factor = 10 ** digits
    return math.floor(value * factor + 0.5) / factor


def _truncate_digits(value: float, digits: int = 2) -> float:
    """直接截断到指定小数位，保持推荐水胶比展示与带入值一致。"""
    factor = 10 ** digits
    return math.trunc(value * factor) / factor


def _empty_workability_result() -> dict:
    """返回工作性实验的空结果，供前端在输入未满足条件时稳定渲染。"""
    return {
        "mc": None,
        "m1": None,
        "m2": None,
        "m3": None,
        "m4": None,
        "mg": None,
        "ms": None,
        "mw": None,
        "ma": None,
        "mb": None,
        "wb": None,
        "bs": None,
        "alpha": None,
        "total": None,
    }


def _empty_strength_mix(label: str = "") -> dict:
    """返回强度实验单组配合比的空结果。"""
    return {
        "label": label,
        "wb": None,
        "bs": None,
        "mc": None,
        "m1": None,
        "m2": None,
        "m3": None,
        "m4": None,
        "mg": None,
        "ms": None,
        "mw": None,
        "ma": None,
        "mb": None,
        "total": None,
    }


def _empty_material_result() -> dict:
    """返回配合比校正、实验室配合比等步骤共用的空材料结果。"""
    return {
        "mc": None,
        "m1": None,
        "m2": None,
        "m3": None,
        "m4": None,
        "mg": None,
        "ms": None,
        "mw": None,
        "ma": None,
        "total": None,
    }


def _empty_trial_materials() -> list[dict]:
    """返回试拌量换算列的空结果。"""
    return [
        {"key": key, "label": label, "trial_val": None}
        for key, label in TRIAL_MATERIALS
    ]


def _component_fractions_from_binder_total(
    binder_total: float,
    cement: float,
    fly_ash: float,
    slag: float,
    micro_bead: float,
    silica_fume: float,
) -> Optional[dict[str, float]]:
    """
    按“胶材总量 mb”计算各胶材组分质量分数。

    该口径与迁移前前端工作性实验 / 校正步骤一致：
    各组分质量分数均以设计胶材总量 mb 为分母。
    """
    if binder_total <= 0 or cement < 0:
        return None

    return {
        "mc": cement / binder_total,
        "m1": fly_ash / binder_total,
        "m2": slag / binder_total,
        "m3": micro_bead / binder_total,
        "m4": silica_fume / binder_total,
    }


def _component_fractions_from_materials(
    cement: float,
    fly_ash: float,
    slag: float,
    micro_bead: float,
    silica_fume: float,
) -> Optional[dict[str, float]]:
    """
    按当前胶材分项质量之和计算比例。

    强度实验迁移前以前端表格中的“当前胶材分项值之和”为分母重算比例，
    而不是直接使用 mb，因此这里保留同一实现方式以保证兼容。
    """
    distribution_total = cement + fly_ash + slag + micro_bead + silica_fume
    if distribution_total <= 0:
        return None

    return {
        "mc": cement / distribution_total,
        "m1": fly_ash / distribution_total,
        "m2": slag / distribution_total,
        "m3": micro_bead / distribution_total,
        "m4": silica_fume / distribution_total,
    }


def _format_delta(value: float) -> str:
    """格式化强度实验标签中的步长显示，保持与前端字符串习惯接近。"""
    return f"{value:g}"


def _calculate_workability_result(
    wb: float,
    beta_s: float,
    mb: float,
    mc: float,
    m1: float,
    m2: float,
    m3: float,
    m4: float,
    mg: float,
    ms: float,
    alpha: float,
    workability_binder_delta: float,
    workability_sand_ratio_delta: float,
    workability_alpha_delta: float,
) -> dict:
    """
    计算工作性实验结果。

    业务规则：
        1. 水胶比保持不变。
        2. 通过调整胶材总量、砂率、外加剂掺量重算每方材料用量。
        3. 调整砂率时保持粗细骨料总量不变，按目标砂率重新分配粗细骨料。
    """
    fractions = _component_fractions_from_binder_total(mb, mc, m1, m2, m3, m4)
    total_aggregate = mg + ms
    if fractions is None or wb <= 0 or beta_s <= 0 or beta_s >= 100 or total_aggregate <= 0 or alpha < 0:
        return _empty_workability_result()

    adjusted_binder = mb + workability_binder_delta
    adjusted_sand_ratio = beta_s + workability_sand_ratio_delta
    adjusted_alpha = alpha + workability_alpha_delta

    if adjusted_binder <= 0 or adjusted_sand_ratio <= 0 or adjusted_sand_ratio >= 100 or adjusted_alpha < 0:
        return _empty_workability_result()

    adjusted_water = adjusted_binder * wb
    adjusted_admixture = adjusted_binder * (adjusted_alpha / 100.0)
    adjusted_sand = total_aggregate * (adjusted_sand_ratio / 100.0)
    adjusted_coarse = total_aggregate - adjusted_sand

    cement = adjusted_binder * fractions["mc"]
    fly_ash = adjusted_binder * fractions["m1"]
    slag = adjusted_binder * fractions["m2"]
    micro_bead = adjusted_binder * fractions["m3"]
    silica_fume = adjusted_binder * fractions["m4"]
    total = sum([
        cement,
        fly_ash,
        slag,
        micro_bead,
        silica_fume,
        adjusted_coarse,
        adjusted_sand,
        adjusted_water,
        adjusted_admixture,
    ])

    return {
        "mc": _round_js(cement, 2),
        "m1": _round_js(fly_ash, 2),
        "m2": _round_js(slag, 2),
        "m3": _round_js(micro_bead, 2),
        "m4": _round_js(silica_fume, 2),
        "mg": _round_js(adjusted_coarse, 2),
        "ms": _round_js(adjusted_sand, 2),
        "mw": _round_js(adjusted_water, 2),
        "ma": _round_js(adjusted_admixture, 2),
        "mb": _round_js(adjusted_binder, 2),
        "wb": _round_js(adjusted_water / adjusted_binder, 4),
        "bs": _round_js(adjusted_sand_ratio, 2),
        "alpha": _round_js(adjusted_alpha, 2),
        "total": _round_js(total, 2),
    }


def _calculate_trial_materials(workability_result: dict, batch_volume: float) -> list[dict]:
    """按试拌体积将工作性实验每方结果换算为批量用量。"""
    if batch_volume <= 0:
        return _empty_trial_materials()

    factor = batch_volume / 1000.0
    rows: list[dict] = []

    for key, label in TRIAL_MATERIALS:
        value = workability_result.get(key)
        rows.append({
            "key": key,
            "label": label,
            "trial_val": None if value is None else _round_js(value * factor, 3),
        })

    return rows


def _calculate_strength_mixes(
    wb: float,
    beta_s: float,
    mb: float,
    mc: float,
    m1: float,
    m2: float,
    m3: float,
    m4: float,
    mg: float,
    ms: float,
    mw: float,
    alpha: float,
    workability_result: dict,
    delta_wb: float,
    delta_bs: float,
    trial_alpha: Optional[float] = None,
    trial_ma0: Optional[float] = None,
    trial_maP: Optional[float] = None,
    trial_maN: Optional[float] = None,
) -> list[dict]:
    """
    计算强度实验三组配合比。

    保持与迁移前前端一致的关键口径：
        1. 以\u201c工作性实验结果\u201d为优先基准；若该结果为空，则回退到设计配合比。
        2. 调整水胶比时保持胶凝材料总量不变，通过水 = 胶材 \u00d7 W/B 重算用水量。
        3. 调整砂率时保持粗细骨料总量不变，一增一降完成重分配。
        4. 外加剂掺量由用户在强度试验页输入（trial_alpha）；未输入时沿用工作性的 alpha。
        5. 各组外加剂用量可由前端表格直接覆盖（trial_ma0/P/N）。
    """
    base_binder = workability_result.get("mb") if workability_result.get("mb") is not None else None
    base_cement = workability_result.get("mc") if workability_result.get("mc") is not None else None
    base_fly_ash = workability_result.get("m1") if workability_result.get("m1") is not None else None
    base_slag = workability_result.get("m2") if workability_result.get("m2") is not None else None
    base_micro_bead = workability_result.get("m3") if workability_result.get("m3") is not None else None
    base_silica_fume = workability_result.get("m4") if workability_result.get("m4") is not None else None
    base_coarse = workability_result.get("mg") if workability_result.get("mg") is not None else None
    base_fine = workability_result.get("ms") if workability_result.get("ms") is not None else None
    base_water = workability_result.get("mw") if workability_result.get("mw") is not None else None
    current_wb = workability_result.get("wb") if workability_result.get("wb") is not None else None
    current_bs = workability_result.get("bs") if workability_result.get("bs") is not None else None
    current_alpha = workability_result.get("alpha") if workability_result.get("alpha") is not None else None

    binder = base_binder if base_binder is not None else mb
    cement = base_cement if base_cement is not None else mc
    fly_ash = base_fly_ash if base_fly_ash is not None else m1
    slag = base_slag if base_slag is not None else m2
    micro_bead = base_micro_bead if base_micro_bead is not None else m3
    silica_fume = base_silica_fume if base_silica_fume is not None else m4
    coarse = base_coarse if base_coarse is not None else mg
    fine = base_fine if base_fine is not None else ms
    water = base_water if base_water is not None else mw
    resolved_wb = current_wb if current_wb is not None else wb
    resolved_bs = current_bs if current_bs is not None else beta_s
    resolved_alpha = current_alpha if current_alpha is not None else alpha

    # 外加剂掺量：优先使用用户在强度试验页输入的 trial_alpha
    strength_alpha = trial_alpha if trial_alpha is not None else resolved_alpha

    if (
        binder is None
        or binder <= 0
        or coarse is None
        or fine is None
        or cement is None
        or resolved_wb is None
        or resolved_wb <= 0
        or resolved_bs is None
        or strength_alpha is None
    ):
        return []


    total_aggregate = coarse + fine
    variants = [
        {"label": "基准", "wb": resolved_wb, "bs": resolved_bs},
        {
            "label": f"W/B+{delta_wb:.2f} βs+{_format_delta(delta_bs)}%",
            "wb": resolved_wb + delta_wb,
            "bs": resolved_bs + delta_bs,
        },
        {
            "label": f"W/B-{delta_wb:.2f} βs-{_format_delta(delta_bs)}%",
            "wb": resolved_wb - delta_wb,
            "bs": resolved_bs - delta_bs,
        },
    ]

    # Per-group admixture overrides: [基准, +Δ, -Δ]
    ma_overrides = [trial_ma0, trial_maP, trial_maN]

    mixes: list[dict] = []
    for idx, variant in enumerate(variants):
        if variant["wb"] <= 0 or variant["bs"] <= 0 or variant["bs"] >= 100:
            mixes.append(_empty_strength_mix(variant["label"]))
            continue

        # 胶材总量不变，水 = 胶材 × W/B
        adjusted_water = binder * variant["wb"]
        if adjusted_water <= 0:
            mixes.append(_empty_strength_mix(variant["label"]))
            continue

        # 各胶材分量保持不变（因为胶材总量不变、比例不变）
        adjusted_cement = cement
        adjusted_fly_ash = fly_ash
        adjusted_slag = slag
        adjusted_micro_bead = micro_bead
        adjusted_silica_fume = silica_fume
        adjusted_sand = total_aggregate * (variant["bs"] / 100.0)
        adjusted_coarse = total_aggregate - adjusted_sand

        # 外加剂：优先使用前端表格直接输入的覆盖值
        ma_override = ma_overrides[idx] if idx < len(ma_overrides) else None
        if ma_override is not None:
            adjusted_admixture = ma_override
        else:
            adjusted_admixture = binder * (strength_alpha / 100.0)

        total = sum([
            adjusted_cement,
            adjusted_fly_ash,
            adjusted_slag,
            adjusted_micro_bead,
            adjusted_silica_fume,
            adjusted_coarse,
            adjusted_sand,
            adjusted_water,
            adjusted_admixture,
        ])

        mixes.append({
            "label": variant["label"],
            "wb": _round_js(variant["wb"], 4),
            "bs": _round_js(variant["bs"], 2),
            "mc": _round_js(adjusted_cement, 2),
            "m1": _round_js(adjusted_fly_ash, 2),
            "m2": _round_js(adjusted_slag, 2),
            "m3": _round_js(adjusted_micro_bead, 2),
            "m4": _round_js(adjusted_silica_fume, 2),
            "mg": _round_js(adjusted_coarse, 2),
            "ms": _round_js(adjusted_sand, 2),
            "mw": _round_js(adjusted_water, 2),
            "ma": _round_js(adjusted_admixture, 2),
            "mb": _round_js(binder, 2),
            "total": _round_js(total, 2),
        })

    return mixes


def _calculate_strength_regression(
    strength_mixes: list[dict],
    strength0: Optional[float],
    strength_p: Optional[float],
    strength_n: Optional[float],
    base_wb: Optional[float],
    target_strength: Optional[float],
) -> Optional[dict]:
    """根据三组强度实验数据做线性回归，并给出推荐水胶比。"""
    strengths = [strength0, strength_p, strength_n]
    if len(strength_mixes) < 3 or any(value is None for value in strengths):
        return None

    pairs: list[tuple[float, float]] = []
    for mix, strength in zip(strength_mixes, strengths):
        mix_wb = mix.get("wb")
        if mix_wb is None or mix_wb <= 0:
            return None
        pairs.append((1.0 / mix_wb, float(strength)))

    count = len(pairs)
    sum_x = sum(pair[0] for pair in pairs)
    sum_y = sum(pair[1] for pair in pairs)
    sum_xy = sum(pair[0] * pair[1] for pair in pairs)
    sum_x2 = sum(pair[0] * pair[0] for pair in pairs)
    denominator = count * sum_x2 - sum_x * sum_x

    if abs(denominator) < 1e-9:
        return None

    a = (count * sum_xy - sum_x * sum_y) / denominator
    b = (sum_y - a * sum_x) / count
    average_y = sum_y / count
    ss_tot = sum((pair[1] - average_y) ** 2 for pair in pairs)
    ss_res = sum((pair[1] - (a * pair[0] + b)) ** 2 for pair in pairs)
    r2 = 1.0 if ss_tot == 0 else 1.0 - ss_res / ss_tot

    recommend_wb = None
    if target_strength is not None and abs(a) > 1e-9:
        recommended_strength = target_strength + RECOMMEND_STRENGTH_MARGIN
        target_cw = (recommended_strength - b) / a
        if target_cw > 0:
            recommend_wb = _truncate_digits(1.0 / target_cw, RECOMMEND_WB_DIGITS)

    predict_strength = None
    if recommend_wb is not None and recommend_wb > 0:
        predict_strength = _round_js(a / recommend_wb + b, 1)

    return {
        "a": _round_js(a, 4),
        "b": _round_js(b, 2),
        "r2": _round_js(r2, 4),
        "recommend_wb": recommend_wb,
        "predict_strength": predict_strength,
    }


def _calculate_chart_data(strength_mixes: list[dict], strength0: Optional[float], strength_p: Optional[float], strength_n: Optional[float]) -> Optional[dict]:
    """生成前端强度关系图所需的坐标范围和散点数据。"""
    strengths = [strength0, strength_p, strength_n]
    if len(strength_mixes) < 3 or any(value is None for value in strengths):
        return None

    bw_ratios: list[float] = []
    for mix in strength_mixes:
        mix_wb = mix.get("wb")
        if mix_wb is None or mix_wb <= 0:
            return None
        bw_ratios.append(_round_js(1.0 / mix_wb, 4))

    strength_values = [float(value) for value in strengths if value is not None]
    raw_min_bw = min(bw_ratios)
    raw_max_bw = max(bw_ratios)
    raw_min_strength = min(strength_values)
    raw_max_strength = max(strength_values)
    min_bw = _round_js(raw_min_bw - 0.05, 4)
    max_bw = _round_js(raw_max_bw + 0.05, 4)
    min_strength = math.floor(raw_min_strength - 2)
    max_strength = math.ceil(raw_max_strength + 2)

    return {
        "min_bw": min_bw,
        "max_bw": max_bw,
        "range_bw": max(max_bw - min_bw, 0.0001),
        "min_strength": min_strength,
        "max_strength": max_strength,
        "range_strength": max(max_strength - min_strength, 0.1),
        "bw_ratios": bw_ratios,
        "strengths": strength_values,
    }


def _calculate_adapt_result(
    wb: float,
    beta_s: float,
    mb: float,
    mc: float,
    m1: float,
    m2: float,
    m3: float,
    m4: float,
    mg: float,
    alpha: float,
    wb_adj: Optional[float],
    mb_adj: Optional[float],
    sand_ratio_adj: Optional[float],
    alpha_adj: Optional[float],
) -> dict:
    """
    计算配合比校正步骤中的“调整配合比”。

    与迁移前前端保持一致：
        1. 以设计胶材总量 mb 计算各胶材分项比例。
        2. 粗骨料保持不变，细骨料按调整后砂率反算。
        3. 水和外加剂分别按调整后 W/B 与 α 重算。
    """
    fractions = _component_fractions_from_binder_total(mb, mc, m1, m2, m3, m4)
    if fractions is None or mg <= 0:
        return _empty_material_result()

    resolved_wb = wb if wb_adj is None else wb_adj
    resolved_mb = mb if mb_adj is None else mb_adj
    resolved_bs = beta_s if sand_ratio_adj is None else sand_ratio_adj
    resolved_alpha = alpha if alpha_adj is None else alpha_adj

    if (
        resolved_wb <= 0
        or resolved_mb <= 0
        or resolved_bs <= 0
        or resolved_bs >= 100
        or resolved_alpha < 0
    ):
        return _empty_material_result()

    sand_ratio_decimal = resolved_bs / 100.0
    cement_mass = resolved_mb * fractions["mc"]
    fly_ash = resolved_mb * fractions["m1"]
    slag = resolved_mb * fractions["m2"]
    micro_bead = resolved_mb * fractions["m3"]
    silica_fume = resolved_mb * fractions["m4"]
    sand = sand_ratio_decimal / (1.0 - sand_ratio_decimal) * mg
    water = resolved_mb * resolved_wb
    admixture = resolved_mb * (resolved_alpha / 100.0)
    total = sum([
        cement_mass,
        fly_ash,
        slag,
        micro_bead,
        silica_fume,
        mg,
        sand,
        water,
        admixture,
    ])

    return {
        "mc": _round_js(cement_mass, 2),
        "m1": _round_js(fly_ash, 2),
        "m2": _round_js(slag, 2),
        "m3": _round_js(micro_bead, 2),
        "m4": _round_js(silica_fume, 2),
        "mg": _round_js(mg, 2),
        "ms": _round_js(sand, 2),
        "mw": _round_js(water, 2),
        "ma": _round_js(admixture, 2),
        "total": _round_js(total, 2),
    }


def _calculate_density_correction_factor(measured_density: Optional[float], calculated_density: Optional[float]) -> Optional[float]:
    """根据实测 / 计算表观密度求统一缩放系数。"""
    if measured_density is None or measured_density <= 0 or calculated_density is None or calculated_density <= 0:
        return None
    return _round_js(measured_density / calculated_density, 6)


def _calculate_lab_mix(adapt_result: dict, density_correction_factor: Optional[float]) -> dict:
    """按表观密度校正系数对调整配合比进行统一放大 / 缩小。"""
    if density_correction_factor is None or density_correction_factor <= 0:
        return _empty_material_result()

    return {
        "mc": _round_js(adapt_result["mc"] * density_correction_factor, 2) if adapt_result["mc"] is not None else None,
        "m1": _round_js(adapt_result["m1"] * density_correction_factor, 2) if adapt_result["m1"] is not None else None,
        "m2": _round_js(adapt_result["m2"] * density_correction_factor, 2) if adapt_result["m2"] is not None else None,
        "m3": _round_js(adapt_result["m3"] * density_correction_factor, 2) if adapt_result["m3"] is not None else None,
        "m4": _round_js(adapt_result["m4"] * density_correction_factor, 2) if adapt_result["m4"] is not None else None,
        "mg": _round_js(adapt_result["mg"] * density_correction_factor, 2) if adapt_result["mg"] is not None else None,
        "ms": _round_js(adapt_result["ms"] * density_correction_factor, 2) if adapt_result["ms"] is not None else None,
        "mw": _round_js(adapt_result["mw"] * density_correction_factor, 2) if adapt_result["mw"] is not None else None,
        "ma": _round_js(adapt_result["ma"] * density_correction_factor, 2) if adapt_result["ma"] is not None else None,
        "total": _round_js(adapt_result["total"] * density_correction_factor, 2) if adapt_result["total"] is not None else None,
    }


def calc_hpc_trial(
    wb: float,
    beta_s: float,
    mb: float,
    mc: float,
    m1: float = 0.0,
    m2: float = 0.0,
    m3: float = 0.0,
    m4: float = 0.0,
    mg: float = 0.0,
    ms: float = 0.0,
    mw: float = 0.0,
    ma: float = 0.0,
    alpha: float = 0.0,
    batch_volume: float = 20.0,
    workability_binder_delta: float = 0.0,
    workability_sand_ratio_delta: float = 0.0,
    workability_alpha_delta: float = 0.0,
    delta_wb: float = 0.02,
    delta_bs: float = 2.0,
    strength0: Optional[float] = None,
    strength_p: Optional[float] = None,
    strength_n: Optional[float] = None,
    target_strength: Optional[float] = None,
    wb_adj: Optional[float] = None,
    mb_adj: Optional[float] = None,
    sand_ratio_adj: Optional[float] = None,
    alpha_adj: Optional[float] = None,
    measured_density: Optional[float] = None,
    trial_alpha: Optional[float] = None,
    trial_ma0: Optional[float] = None,
    trial_maP: Optional[float] = None,
    trial_maN: Optional[float] = None,
) -> dict:
    """
    高性能试配统一计算入口。

    说明：
        - 入参全部使用当前页面已有值，避免后端依赖额外上下文。
        - 返回值覆盖工作性、强度、校正三步所需全部派生结果。
        - 纯界面状态（如工作性文字说明、是否满足要求）继续由前端维护，不纳入服务端计算。
    """
    workability_result = _calculate_workability_result(
        wb=wb,
        beta_s=beta_s,
        mb=mb,
        mc=mc,
        m1=m1,
        m2=m2,
        m3=m3,
        m4=m4,
        mg=mg,
        ms=ms,
        alpha=alpha,
        workability_binder_delta=workability_binder_delta,
        workability_sand_ratio_delta=workability_sand_ratio_delta,
        workability_alpha_delta=workability_alpha_delta,
    )
    trial_materials = _calculate_trial_materials(workability_result, batch_volume)
    base_wb = workability_result["wb"] if workability_result["wb"] is not None else wb
    base_bs = workability_result["bs"] if workability_result["bs"] is not None else beta_s
    base_alpha = workability_result["alpha"] if workability_result["alpha"] is not None else alpha

    strength_mixes = _calculate_strength_mixes(
        wb=wb,
        beta_s=beta_s,
        mb=mb,
        mc=mc,
        m1=m1,
        m2=m2,
        m3=m3,
        m4=m4,
        mg=mg,
        ms=ms,
        mw=mw,
        alpha=alpha,
        workability_result=workability_result,
        delta_wb=delta_wb,
        delta_bs=delta_bs,
        trial_alpha=trial_alpha,
        trial_ma0=trial_ma0,
        trial_maP=trial_maP,
        trial_maN=trial_maN,
    )
    strength_regression = _calculate_strength_regression(
        strength_mixes=strength_mixes,
        strength0=strength0,
        strength_p=strength_p,
        strength_n=strength_n,
        base_wb=base_wb,
        target_strength=target_strength,
    )
    chart_data = _calculate_chart_data(strength_mixes, strength0, strength_p, strength_n)

    adapt_result = _calculate_adapt_result(
        wb=wb,
        beta_s=beta_s,
        mb=mb,
        mc=mc,
        m1=m1,
        m2=m2,
        m3=m3,
        m4=m4,
        mg=mg,
        alpha=alpha,
        wb_adj=wb_adj,
        mb_adj=mb_adj,
        sand_ratio_adj=sand_ratio_adj,
        alpha_adj=alpha_adj,
    )
    calculated_density = adapt_result["total"]
    density_correction_factor = _calculate_density_correction_factor(measured_density, calculated_density)
    lab_mix = _calculate_lab_mix(adapt_result, density_correction_factor)

    return {
        "base_wb": base_wb,
        "base_bs": base_bs,
        "base_alpha": base_alpha,
        "workability_result": workability_result,
        "trial_materials": trial_materials,
        "strength_mixes": strength_mixes,
        "strength_regression": strength_regression,
        "chart_data": chart_data,
        "adapt_result": adapt_result,
        "calculated_density": calculated_density,
        "density_correction_factor": density_correction_factor,
        "lab_mix": lab_mix,
    }