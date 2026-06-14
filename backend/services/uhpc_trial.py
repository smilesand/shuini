"""
超高性能混凝土试配服务端计算
==========================
将前端 TrialUhpcView 中的试配计算逻辑统一迁移到服务端，
与高性能试配 hpc_trial.py 保持相同的架构风格。
"""

from __future__ import annotations
from typing import Optional


def _round_js(value: float, digits: int) -> float:
    """与前端 `Number.toFixed` 行为对齐的截断式舍入。"""
    factor = 10 ** digits
    return float(f"{round(value * factor) / factor:.{digits}f}")


def _truncate_digits(value: float, digits: int) -> float:
    """直接截断到指定位数（不四舍五入）。"""
    factor = 10 ** digits
    return float(f"{int(value * factor) / factor:.{digits}f}")


def _empty_mix() -> dict:
    return {
        "cement": 0.0,
        "fly_ash": 0.0,
        "micro_bead": 0.0,
        "silica_fume": 0.0,
        "sand": 0.0,
        "steel_fiber": 0.0,
        "water": 0.0,
        "admixture": 0.0,
        "binder": 0.0,
        "total": 0.0,
        "admixture_pct": 0.0,
    }


def _calc_mix(
    wb: float,
    sb: float,
    alpha: float,
    sf_mass: float,
    total: float,
    cement_pct: float,
    silica_fume_pct: float,
    fly_ash_pct: float,
    micro_bead_pct: float,
    sf_delta: float = 0.0,
    admix_override: Optional[float] = None,
) -> dict:
    """核心配合比重算逻辑，与前端 calcMix 完全对齐。"""
    binder = (total - sf_mass) / (1.0 + sb + wb + alpha / 100.0)
    if binder <= 0:
        return _empty_mix()

    ce_pct = cement_pct - sf_delta
    sf_pct = silica_fume_pct + sf_delta

    # 约束：ce_pct 和 sf_pct 不能为负，超出部分限制在对方身上
    if sf_pct < 0.0:
        ce_pct = cement_pct + silica_fume_pct  # 硅灰归零，差值还给水泥
        sf_pct = 0.0
    if ce_pct < 0.0:
        sf_pct = cement_pct + silica_fume_pct  # 水泥归零，差值还给硅灰
        ce_pct = 0.0

    cement = binder * ce_pct / 100.0
    fly_ash = binder * fly_ash_pct / 100.0
    micro_bead = binder * micro_bead_pct / 100.0
    silica_fume = binder * sf_pct / 100.0
    sand = binder * sb
    water_mass = binder * wb
    admixture = admix_override if admix_override is not None else binder * alpha / 100.0
    result_total = binder * (1.0 + sb + wb) + sf_mass + admixture
    admixture_pct = admixture / binder * 100.0 if binder > 0 else 0.0

    return {
        "cement": _round_js(cement, 1),
        "fly_ash": _round_js(fly_ash, 1),
        "micro_bead": _round_js(micro_bead, 1),
        "silica_fume": _round_js(silica_fume, 1),
        "sand": _round_js(sand, 1),
        "steel_fiber": _round_js(sf_mass, 1),
        "water": _round_js(water_mass, 1),
        "admixture": _round_js(admixture, 1),
        "binder": _round_js(binder, 1),
        "total": _round_js(result_total, 1),
        "admixture_pct": _round_js(admixture_pct, 2),
    }


def _lerp(x1: float, y1: float, x2: float, y2: float, t_y: float) -> float:
    """线性插值，与前端 lerp 行为对齐。"""
    if abs(y2 - y1) < 0.001:
        return (x1 + x2) / 2.0
    r = x1 + (x2 - x1) * (t_y - y1) / (y2 - y1)
    return max(min(r, max(x1, x2)), min(x1, x2))


def _linear_fit(x1: float, y1: float, x2: float, y2: float, x3: float, y3: float, t_y: float) -> float:
    """三点最小二乘线性回归，返回目标强度 t_y 对应的 x 值。"""
    xs = [x1, x2, x3]
    ys = [y1, y2, y3]
    n = 3
    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)
    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-9:
        return (x1 + x2 + x3) / 3.0
    a = (n * sum_xy - sum_x * sum_y) / denom
    b = (sum_y - a * sum_x) / n
    if abs(a) < 1e-9:
        return (x1 + x2 + x3) / 3.0
    result = (t_y - b) / a
    lo, hi = min(xs), max(xs)
    return max(min(result, hi), lo)

def _linear_predict(x1: float, y1: float, x2: float, y2: float, x3: float, y3: float, t_x: float) -> float:
    """三点最小二乘线性回归，供已知 x 预测 y 使用（如预测外加剂用量）。"""
    xs = [x1, x2, x3]
    ys = [y1, y2, y3]
    n = 3
    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)
    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-9:
        return (y1 + y2 + y3) / 3.0
    a = (n * sum_xy - sum_x * sum_y) / denom
    b = (sum_y - a * sum_x) / n
    return a * t_x + b


def _calc_density_correction(
    measured_density: Optional[float],
    calc_density: Optional[float],
) -> tuple[Optional[float], Optional[float], bool]:
    """表观密度校正系数与是否需要校正的判断。"""
    if measured_density is None or measured_density <= 0:
        return None, None, False
    if calc_density is None or calc_density <= 0:
        return None, None, False

    factor = _round_js(measured_density / calc_density, 6)
    needs = abs(measured_density - calc_density) / calc_density > 0.02
    return factor, factor, needs


def _apply_correction(mix: dict, factor: Optional[float]) -> dict:
    """对配合比各组分按统一校正系数缩放。"""
    if factor is None or factor <= 0:
        return _empty_mix()

    res = {
        key: _round_js(mix[key] * factor, 1) if mix.get(key) is not None else 0.0
        for key in _empty_mix() if key != "admixture_pct"
    }
    # 百分比不应该乘系数
    res["admixture_pct"] = mix.get("admixture_pct", 0.0)
    return res


def calc_uhpc_trial(
    *,
    wb: float,
    sb: float,
    alpha: float,
    sf_mass: float,
    total: float,
    cement_pct: float,
    fly_ash_pct: float,
    micro_bead_pct: float,
    silica_fume_pct: float,
    design_strength: float,
    adjusted_sb: Optional[float],
    adjusted_alpha: Optional[float],
    s_wb_0: Optional[float],
    s_wb_plus: Optional[float],
    s_wb_minus: Optional[float],
    s_sf_plus: Optional[float],
    s_sf_minus: Optional[float],
    a_wb_plus: Optional[float],
    a_wb_minus: Optional[float],
    a_sf_plus: Optional[float],
    a_sf_minus: Optional[float],
    corr_base: str,
    measured_density: Optional[float],
) -> dict:
    """统一计算超高性能试配的全部派生结果。"""

    trial_sb = adjusted_sb if adjusted_sb is not None else sb
    trial_alpha = adjusted_alpha if adjusted_alpha is not None else alpha

    # ── Tab 1: 试拌配合比 ──────────────────────────────────────────
    trial_mix = _calc_mix(wb, trial_sb, trial_alpha, sf_mass, total,
                          cement_pct, silica_fume_pct, fly_ash_pct, micro_bead_pct)

    # ── Tab 2: 强度变体 ────────────────────────────────────────────
    variant_wb_plus = _calc_mix(wb + 0.01, trial_sb, trial_alpha, sf_mass, total,
                                cement_pct, silica_fume_pct, fly_ash_pct, micro_bead_pct,
                                admix_override=a_wb_plus)
    variant_wb_minus = _calc_mix(wb - 0.01, trial_sb, trial_alpha, sf_mass, total,
                                 cement_pct, silica_fume_pct, fly_ash_pct, micro_bead_pct,
                                 admix_override=a_wb_minus)
    variant_sf_plus = _calc_mix(wb, trial_sb, trial_alpha, sf_mass, total,
                                cement_pct, silica_fume_pct, fly_ash_pct, micro_bead_pct, sf_delta=5.0,
                                admix_override=a_sf_plus)
    variant_sf_minus = _calc_mix(wb, trial_sb, trial_alpha, sf_mass, total,
                                 cement_pct, silica_fume_pct, fly_ash_pct, micro_bead_pct, sf_delta=-5.0,
                                 admix_override=a_sf_minus)

    # 强度推荐 – 三点线性回归
    rec_wb = None
    rec_sf = None
    if s_wb_0 is not None and s_wb_plus is not None and s_wb_minus is not None:
        rec_wb = _truncate_digits(
            _linear_fit(wb, s_wb_0, wb + 0.01, s_wb_plus, wb - 0.01, s_wb_minus, design_strength), 3)
    if s_wb_0 is not None and s_sf_plus is not None and s_sf_minus is not None:
        base_sf = trial_mix["silica_fume"]
        rec_sf = _truncate_digits(
            _linear_fit(base_sf, s_wb_0,
                        variant_sf_plus["silica_fume"], s_sf_plus,
                        variant_sf_minus["silica_fume"], s_sf_minus,
                        design_strength), 1)

    # ── Tab 3: 校正配合比 ──────────────────────────────────────────
    if corr_base == "wbRec" and rec_wb is not None:
        # 提取各自实际掺量(%)
        alpha_base = trial_mix["admixture"] / trial_mix["binder"] * 100.0 if trial_mix["binder"] > 0 else trial_alpha
        alpha_plus = variant_wb_plus["admixture"] / variant_wb_plus["binder"] * 100.0 if variant_wb_plus["binder"] > 0 else trial_alpha
        alpha_minus = variant_wb_minus["admixture"] / variant_wb_minus["binder"] * 100.0 if variant_wb_minus["binder"] > 0 else trial_alpha
        
        fitted_alpha = _linear_predict(
            wb, alpha_base,
            wb + 0.01, alpha_plus,
            wb - 0.01, alpha_minus,
            rec_wb
        )
        fitted_alpha = max(0.0, fitted_alpha)
        corr_mix = _calc_mix(rec_wb, trial_sb, fitted_alpha, sf_mass, total,
                             cement_pct, silica_fume_pct, fly_ash_pct, micro_bead_pct)
    elif corr_base == "sfRec" and rec_sf is not None:
        binder = trial_mix["binder"]
        if binder > 0:
            new_sf_pct = rec_sf / binder * 100.0
            orig_sf_pct = silica_fume_pct
            adjusted_ce_pct = cement_pct - (new_sf_pct - orig_sf_pct)
            
            base_sf = trial_mix["silica_fume"]
            alpha_base = trial_mix["admixture"] / trial_mix["binder"] * 100.0
            alpha_plus = variant_sf_plus["admixture"] / variant_sf_plus["binder"] * 100.0 if variant_sf_plus["binder"] > 0 else trial_alpha
            alpha_minus = variant_sf_minus["admixture"] / variant_sf_minus["binder"] * 100.0 if variant_sf_minus["binder"] > 0 else trial_alpha

            fitted_alpha = _linear_predict(
                base_sf, alpha_base,
                variant_sf_plus["silica_fume"], alpha_plus,
                variant_sf_minus["silica_fume"], alpha_minus,
                rec_sf
            )
            fitted_alpha = max(0.0, fitted_alpha)

            corr_mix = _calc_mix(wb, trial_sb, fitted_alpha, sf_mass, total,
                                 adjusted_ce_pct, new_sf_pct, fly_ash_pct, micro_bead_pct)
        else:
            corr_mix = _empty_mix()
    else:
        corr_mix = trial_mix

    # 密度校正
    calc_density = corr_mix["total"] if corr_mix["total"] > 0 else None
    corr_factor, _, needs_corr = _calc_density_correction(measured_density, calc_density)
    lab_mix = _apply_correction(corr_mix, corr_factor) if needs_corr else corr_mix

    return {
        "design_strength": design_strength,
        "trial_sb": trial_sb,
        "trial_alpha": trial_alpha,
        "trial_mix": trial_mix,
        "variant_wb_plus": variant_wb_plus,
        "variant_wb_minus": variant_wb_minus,
        "variant_sf_plus": variant_sf_plus,
        "variant_sf_minus": variant_sf_minus,
        "rec_wb": rec_wb,
        "rec_sf": rec_sf,
        "corr_base": corr_base,
        "corr_mix": corr_mix,
        "calc_density": calc_density,
        "corr_factor": corr_factor,
        "needs_corr": needs_corr,
        "lab_mix": lab_mix,
    }
