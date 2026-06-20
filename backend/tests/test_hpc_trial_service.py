"""
高性能试配服务一致性校验
========================
本测试文件保留一份“迁移前前端公式”的 Python 基线实现，
并将其与新的后端统一服务逐字段对比，验证服务端迁移没有改变既有计算口径。
"""

from __future__ import annotations

import math
import unittest
from typing import Any, Optional

from services.hpc_trial import calc_hpc_trial


TRIAL_MATERIALS = (
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


def js_round(value: float, digits: int = 4) -> float:
    """复现迁移前前端使用的 Math.round 风格舍入。"""
    factor = 10 ** digits
    return math.floor(value * factor + 0.5) / factor


def js_truncate(value: float, digits: int = 2) -> float:
    """复现推荐水胶比只保留前两位小数的截断规则。"""
    factor = 10 ** digits
    return math.trunc(value * factor) / factor


def empty_workability_result() -> dict[str, Any]:
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


def empty_strength_mix(label: str = "") -> dict[str, Any]:
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


def empty_material_result() -> dict[str, Any]:
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


def empty_trial_materials() -> list[dict[str, Any]]:
    return [
        {"key": key, "label": label, "trial_val": None}
        for key, label in TRIAL_MATERIALS
    ]


def legacy_workability(payload: dict[str, Any]) -> dict[str, Any]:
    binder = payload["mb"]
    coarse = payload["mg"]
    fine = payload["ms"]
    base_wb = payload["wb"]
    base_sand_ratio = payload["beta_s"]
    base_alpha = payload["alpha"]
    cement_ratio = payload["mc"] / binder if binder > 0 else None
    b1_fraction = payload["m1"] / binder if binder and payload["m1"] is not None else 0
    b2_fraction = payload["m2"] / binder if binder and payload["m2"] is not None else 0
    b3_fraction = payload["m3"] / binder if binder and payload["m3"] is not None else 0
    b4_fraction = payload["m4"] / binder if binder and payload["m4"] is not None else 0

    if (
        binder is None
        or binder <= 0
        or coarse is None
        or fine is None
        or base_wb is None
        or base_wb <= 0
        or base_sand_ratio is None
        or base_alpha is None
        or cement_ratio is None
    ):
        return empty_workability_result()

    adjusted_binder = binder + payload["workability_binder_delta"]
    adjusted_sand_ratio = base_sand_ratio + payload["workability_sand_ratio_delta"]
    adjusted_alpha = base_alpha + payload["workability_alpha_delta"]

    if adjusted_binder <= 0 or adjusted_sand_ratio <= 0 or adjusted_sand_ratio >= 100 or adjusted_alpha < 0:
        return empty_workability_result()

    adjusted_water = adjusted_binder * base_wb
    adjusted_admixture = adjusted_binder * (adjusted_alpha / 100.0)
    adjusted_wb = adjusted_water / adjusted_binder
    total_aggregate = coarse + fine
    adjusted_sand = total_aggregate * (adjusted_sand_ratio / 100.0)
    adjusted_coarse = total_aggregate - adjusted_sand
    cement = adjusted_binder * cement_ratio
    fly_ash = adjusted_binder * b1_fraction
    slag = adjusted_binder * b2_fraction
    micro_bead = adjusted_binder * b3_fraction
    silica_fume = adjusted_binder * b4_fraction
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
        "mc": js_round(cement, 2),
        "m1": js_round(fly_ash, 2),
        "m2": js_round(slag, 2),
        "m3": js_round(micro_bead, 2),
        "m4": js_round(silica_fume, 2),
        "mg": js_round(adjusted_coarse, 2),
        "ms": js_round(adjusted_sand, 2),
        "mw": js_round(adjusted_water, 2),
        "ma": js_round(adjusted_admixture, 2),
        "mb": js_round(adjusted_binder, 2),
        "wb": js_round(adjusted_wb, 4),
        "bs": js_round(adjusted_sand_ratio, 2),
        "alpha": js_round(adjusted_alpha, 2),
        "total": js_round(total, 2),
    }


def legacy_trial_materials(workability_result: dict[str, Any], batch_volume: float) -> list[dict[str, Any]]:
    if batch_volume <= 0:
        return empty_trial_materials()

    factor = batch_volume / 1000.0
    rows: list[dict[str, Any]] = []
    for key, label in TRIAL_MATERIALS:
        value = workability_result[key]
        rows.append({
            "key": key,
            "label": label,
            "trial_val": None if value is None else js_round(value * factor, 3),
        })
    return rows


def legacy_strength_mixes(payload: dict[str, Any], workability_result: dict[str, Any]) -> list[dict[str, Any]]:
    binder = workability_result["mb"] if workability_result["mb"] is not None else payload["mb"]
    coarse_aggregate = workability_result["mg"] if workability_result["mg"] is not None else payload["mg"]
    fine_aggregate = workability_result["ms"] if workability_result["ms"] is not None else payload["ms"]
    water = workability_result["mw"] if workability_result["mw"] is not None else payload["mw"]
    cement = workability_result["mc"] if workability_result["mc"] is not None else payload["mc"]
    fly_ash = workability_result["m1"] if workability_result["m1"] is not None else payload["m1"]
    slag = workability_result["m2"] if workability_result["m2"] is not None else payload["m2"]
    micro_bead = workability_result["m3"] if workability_result["m3"] is not None else payload["m3"]
    silica_fume = workability_result["m4"] if workability_result["m4"] is not None else payload["m4"]
    current_wb = workability_result["wb"] if workability_result["wb"] is not None else payload["wb"]
    current_bs = workability_result["bs"] if workability_result["bs"] is not None else payload["beta_s"]
    current_alpha = workability_result["alpha"] if workability_result["alpha"] is not None else payload["alpha"]

    if (
        binder is None
        or binder <= 0
        or coarse_aggregate is None
        or fine_aggregate is None
        or water is None
        or water <= 0
        or cement is None
        or current_wb is None
        or current_bs is None
    ):
        return []

    total_aggregate = coarse_aggregate + fine_aggregate

    # 强度实验外加剂掺量：未提供强度试验页输入时沿用工作性的 alpha。
    strength_alpha = current_alpha

    variants = [
        {"label": "基准", "wb": current_wb, "bs": current_bs},
        {
            "label": f"W/B+{payload['delta_wb']:.2f} βs+{payload['delta_bs']:g}%",
            "wb": current_wb + payload["delta_wb"],
            "bs": current_bs + payload["delta_bs"],
        },
        {
            "label": f"W/B-{payload['delta_wb']:.2f} βs-{payload['delta_bs']:g}%",
            "wb": current_wb - payload["delta_wb"],
            "bs": current_bs - payload["delta_bs"],
        },
    ]

    mixes: list[dict[str, Any]] = []
    for variant in variants:
        if variant["wb"] <= 0 or variant["bs"] <= 0 or variant["bs"] >= 100:
            mixes.append(empty_strength_mix(variant["label"]))
            continue

        # 胶材总量保持不变，水 = 胶材 × W/B 重算用水量。
        adjusted_water = binder * variant["wb"]
        if adjusted_water <= 0:
            mixes.append(empty_strength_mix(variant["label"]))
            continue

        # 各胶材分项保持不变（胶材总量与比例均不变）。
        adjusted_cement = cement
        adjusted_fly_ash = fly_ash
        adjusted_slag = slag
        adjusted_micro_bead = micro_bead
        adjusted_silica_fume = silica_fume
        sand = total_aggregate * (variant["bs"] / 100.0)
        coarse = total_aggregate - sand
        admixture = binder * (strength_alpha / 100.0) if strength_alpha is not None else 0
        total = sum([
            adjusted_cement,
            adjusted_fly_ash,
            adjusted_slag,
            adjusted_micro_bead,
            adjusted_silica_fume,
            coarse,
            sand,
            adjusted_water,
            admixture,
        ])

        mixes.append({
            "label": variant["label"],
            "wb": js_round(variant["wb"], 4),
            "bs": js_round(variant["bs"], 2),
            "mc": js_round(adjusted_cement, 2),
            "m1": js_round(adjusted_fly_ash, 2),
            "m2": js_round(adjusted_slag, 2),
            "m3": js_round(adjusted_micro_bead, 2),
            "m4": js_round(adjusted_silica_fume, 2),
            "mg": js_round(coarse, 2),
            "ms": js_round(sand, 2),
            "mw": js_round(adjusted_water, 2),
            "ma": js_round(admixture, 2),
            "mb": js_round(binder, 2),
            "total": js_round(total, 2),
        })

    return mixes


def legacy_strength_regression(
    strength_mixes: list[dict[str, Any]],
    strength0: Optional[float],
    strength_p: Optional[float],
    strength_n: Optional[float],
    base_wb: Optional[float],
    target_strength: Optional[float],
) -> Optional[dict[str, Any]]:
    strengths = [strength0, strength_p, strength_n]
    if len(strength_mixes) < 3 or any(value is None for value in strengths):
        return None

    pairs: list[tuple[Optional[float], float]] = []
    for mix, strength in zip(strength_mixes, strengths):
        pairs.append((1 / mix["wb"] if mix["wb"] is not None and mix["wb"] > 0 else None, float(strength)))

    if any(pair[0] is None for pair in pairs):
        return None

    count = len(pairs)
    sum_x = sum(pair[0] for pair in pairs if pair[0] is not None)
    sum_y = sum(pair[1] for pair in pairs)
    sum_xy = sum((pair[0] or 0) * pair[1] for pair in pairs)
    sum_x2 = sum((pair[0] or 0) * (pair[0] or 0) for pair in pairs)
    denominator = count * sum_x2 - sum_x * sum_x

    if abs(denominator) < 1e-9:
        return None

    a = (count * sum_xy - sum_x * sum_y) / denominator
    b = (sum_y - a * sum_x) / count
    average_y = sum_y / count
    ss_tot = 0.0
    ss_res = 0.0

    for pair in pairs:
        x = float(pair[0])
        predicted = a * x + b
        ss_res += (pair[1] - predicted) ** 2
        ss_tot += (pair[1] - average_y) ** 2

    r2 = 1 if ss_tot == 0 else 1 - ss_res / ss_tot
    recommend_wb = None
    if target_strength is not None and abs(a) > 1e-9:
        recommended_strength = target_strength + RECOMMEND_STRENGTH_MARGIN
        target_cw = (recommended_strength - b) / a
        if target_cw > 0:
            recommend_wb = js_truncate(1 / target_cw, RECOMMEND_WB_DIGITS)

    predict_strength = None
    if recommend_wb is not None and recommend_wb > 0:
        predict_strength = js_round(a / recommend_wb + b, 1)

    return {
        "a": js_round(a, 4),
        "b": js_round(b, 2),
        "r2": js_round(r2, 4),
        "recommend_wb": recommend_wb,
        "predict_strength": predict_strength,
    }


def legacy_chart_data(strength_mixes: list[dict[str, Any]], strength0: Optional[float], strength_p: Optional[float], strength_n: Optional[float]) -> Optional[dict[str, Any]]:
    strengths = [strength0, strength_p, strength_n]
    if len(strength_mixes) < 3 or any(value is None for value in strengths):
        return None

    bw_ratios: list[Optional[float]] = []
    for mix in strength_mixes:
        bw_ratios.append(js_round(1 / mix["wb"], 4) if mix["wb"] is not None and mix["wb"] > 0 else None)

    if any(value is None for value in bw_ratios):
        return None

    ratio_values = [float(value) for value in bw_ratios if value is not None]
    strength_values = [float(value) for value in strengths if value is not None]
    raw_min_bw = min(ratio_values)
    raw_max_bw = max(ratio_values)
    raw_min_strength = min(strength_values)
    raw_max_strength = max(strength_values)
    min_bw = js_round(raw_min_bw - 0.05, 4)
    max_bw = js_round(raw_max_bw + 0.05, 4)
    min_strength = math.floor(raw_min_strength - 2)
    max_strength = math.ceil(raw_max_strength + 2)

    return {
        "min_bw": min_bw,
        "max_bw": max_bw,
        "range_bw": max(max_bw - min_bw, 0.0001),
        "min_strength": min_strength,
        "max_strength": max_strength,
        "range_strength": max(max_strength - min_strength, 0.1),
        "bw_ratios": ratio_values,
        "strengths": strength_values,
    }


def legacy_adapt_result(payload: dict[str, Any]) -> dict[str, Any]:
    binder = payload["mb_adj"] if payload["mb_adj"] is not None else payload["mb"]
    sand_ratio = payload["sand_ratio_adj"] if payload["sand_ratio_adj"] is not None else payload["beta_s"]
    water_binder_ratio = payload["wb_adj"] if payload["wb_adj"] is not None else payload["wb"]
    admixture_ratio = payload["alpha_adj"] if payload["alpha_adj"] is not None else payload["alpha"]
    aggregate = payload["mg"]
    cement_fraction = payload["mc"] / payload["mb"] if payload["mb"] > 0 else None
    b1_fraction = payload["m1"] / payload["mb"] if payload["mb"] and payload["m1"] is not None else 0
    b2_fraction = payload["m2"] / payload["mb"] if payload["mb"] and payload["m2"] is not None else 0
    b3_fraction = payload["m3"] / payload["mb"] if payload["mb"] and payload["m3"] is not None else 0
    b4_fraction = payload["m4"] / payload["mb"] if payload["mb"] and payload["m4"] is not None else 0

    if (
        binder is None
        or binder <= 0
        or sand_ratio is None
        or sand_ratio <= 0
        or sand_ratio >= 100
        or water_binder_ratio is None
        or water_binder_ratio <= 0
        or admixture_ratio is None
        or admixture_ratio < 0
        or aggregate is None
        or aggregate <= 0
        or cement_fraction is None
    ):
        return empty_material_result()

    sand_ratio_decimal = sand_ratio / 100.0
    admixture_decimal = admixture_ratio / 100.0
    cement_mass = binder * cement_fraction
    m1 = binder * b1_fraction
    m2 = binder * b2_fraction
    m3 = binder * b3_fraction
    m4 = binder * b4_fraction
    sand = sand_ratio_decimal / (1 - sand_ratio_decimal) * aggregate
    water = binder * water_binder_ratio
    admixture = binder * admixture_decimal
    total = sum([cement_mass, m1, m2, m3, m4, aggregate, sand, water, admixture])

    return {
        "mc": js_round(cement_mass, 2),
        "m1": js_round(m1, 2),
        "m2": js_round(m2, 2),
        "m3": js_round(m3, 2),
        "m4": js_round(m4, 2),
        "mg": js_round(aggregate, 2),
        "ms": js_round(sand, 2),
        "mw": js_round(water, 2),
        "ma": js_round(admixture, 2),
        "total": js_round(total, 2),
    }


def legacy_lab_mix(adapt_result: dict[str, Any], measured_density: Optional[float]) -> tuple[Optional[float], dict[str, Any]]:
    calculated_density = adapt_result["total"]
    if (
        measured_density is None
        or measured_density <= 0
        or calculated_density is None
        or calculated_density <= 0
    ):
        return None, empty_material_result()

    correction_factor = js_round(measured_density / calculated_density, 6)

    def apply_factor(value: Optional[float]) -> Optional[float]:
        return js_round(value * correction_factor, 2) if value is not None else None

    return correction_factor, {
        "mc": apply_factor(adapt_result["mc"]),
        "m1": apply_factor(adapt_result["m1"]),
        "m2": apply_factor(adapt_result["m2"]),
        "m3": apply_factor(adapt_result["m3"]),
        "m4": apply_factor(adapt_result["m4"]),
        "mg": apply_factor(adapt_result["mg"]),
        "ms": apply_factor(adapt_result["ms"]),
        "mw": apply_factor(adapt_result["mw"]),
        "ma": apply_factor(adapt_result["ma"]),
        "total": apply_factor(adapt_result["total"]),
    }


def legacy_trial(payload: dict[str, Any]) -> dict[str, Any]:
    workability_result = legacy_workability(payload)
    trial_materials = legacy_trial_materials(workability_result, payload["batch_volume"])
    base_wb = workability_result["wb"] if workability_result["wb"] is not None else payload["wb"]
    base_bs = workability_result["bs"] if workability_result["bs"] is not None else payload["beta_s"]
    base_alpha = workability_result["alpha"] if workability_result["alpha"] is not None else payload["alpha"]
    strength_mixes = legacy_strength_mixes(payload, workability_result)
    strength_regression = legacy_strength_regression(
        strength_mixes,
        payload["strength0"],
        payload["strength_p"],
        payload["strength_n"],
        base_wb,
        payload["target_strength"],
    )
    chart_data = legacy_chart_data(
        strength_mixes,
        payload["strength0"],
        payload["strength_p"],
        payload["strength_n"],
    )
    adapt_result = legacy_adapt_result(payload)
    density_correction_factor, lab_mix = legacy_lab_mix(adapt_result, payload["measured_density"])

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
        "calculated_density": adapt_result["total"],
        "density_correction_factor": density_correction_factor,
        "lab_mix": lab_mix,
    }


class HpcTrialServiceParityTests(unittest.TestCase):
    """验证新的服务端统一计算与迁移前前端公式输出一致。"""

    def assert_nested_equal(self, actual: Any, expected: Any, path: str = "root"):
        """递归比较复杂结构，浮点数使用近似比较，其余值要求完全一致。"""
        if isinstance(expected, dict):
            self.assertIsInstance(actual, dict, msg=path)
            self.assertEqual(set(actual.keys()), set(expected.keys()), msg=path)
            for key in expected:
                self.assert_nested_equal(actual[key], expected[key], f"{path}.{key}")
            return

        if isinstance(expected, list):
            self.assertIsInstance(actual, list, msg=path)
            self.assertEqual(len(actual), len(expected), msg=path)
            for index, (actual_item, expected_item) in enumerate(zip(actual, expected)):
                self.assert_nested_equal(actual_item, expected_item, f"{path}[{index}]")
            return

        if isinstance(expected, float):
            self.assertAlmostEqual(actual, expected, places=9, msg=path)
            return

        self.assertEqual(actual, expected, msg=path)

    def test_service_matches_legacy_frontend_formulas_for_full_trial_flow(self):
        """全量输入场景：覆盖工作性、强度回归、校正与实验室配合比三步。"""
        payload = {
            "wb": 0.3125,
            "beta_s": 43.5,
            "mb": 520.0,
            "mc": 312.0,
            "m1": 104.0,
            "m2": 72.8,
            "m3": 15.6,
            "m4": 15.6,
            "mg": 845.0,
            "ms": 651.46,
            "mw": 162.5,
            "ma": 8.32,
            "alpha": 1.6,
            "batch_volume": 20.0,
            "workability_binder_delta": 15.0,
            "workability_sand_ratio_delta": 1.5,
            "workability_alpha_delta": 0.1,
            "delta_wb": 0.02,
            "delta_bs": 2.0,
            "strength0": 82.3,
            "strength_p": 86.4,
            "strength_n": 78.5,
            "target_strength": 88.0,
            "wb_adj": 0.3015,
            "mb_adj": 540.0,
            "sand_ratio_adj": 44.2,
            "alpha_adj": 1.8,
            "measured_density": 2440.0,
        }

        expected = legacy_trial(payload)
        actual = calc_hpc_trial(**payload)
        self.assert_nested_equal(actual, expected)

    def test_recommend_wb_uses_margin_and_truncation(self):
        """推荐水胶比应按略高于目标强度取值，并直接截断到两位小数。"""
        payload = {
            "wb": 0.3125,
            "beta_s": 43.5,
            "mb": 520.0,
            "mc": 312.0,
            "m1": 104.0,
            "m2": 72.8,
            "m3": 15.6,
            "m4": 15.6,
            "mg": 845.0,
            "ms": 651.46,
            "mw": 162.5,
            "ma": 8.32,
            "alpha": 1.6,
            "batch_volume": 20.0,
            "workability_binder_delta": 15.0,
            "workability_sand_ratio_delta": 1.5,
            "workability_alpha_delta": 0.1,
            "delta_wb": 0.02,
            "delta_bs": 2.0,
            "strength0": 82.3,
            "strength_p": 86.4,
            "strength_n": 78.5,
            "target_strength": 88.0,
            "wb_adj": None,
            "mb_adj": None,
            "sand_ratio_adj": None,
            "alpha_adj": None,
            "measured_density": None,
        }

        actual = calc_hpc_trial(**payload)
        regression = actual["strength_regression"]
        self.assertIsNotNone(regression)

        expected = legacy_strength_regression(
            actual["strength_mixes"],
            payload["strength0"],
            payload["strength_p"],
            payload["strength_n"],
            actual["base_wb"],
            payload["target_strength"],
        )
        self.assertEqual(regression["recommend_wb"], expected["recommend_wb"])
        self.assertEqual(regression["recommend_wb"], js_truncate(regression["recommend_wb"], 2))

    def test_service_matches_legacy_frontend_formulas_for_sparse_optional_inputs(self):
        """稀疏输入场景：覆盖无掺合料、无强度回归、无密度校正时的空结果口径。"""
        payload = {
            "wb": 0.285,
            "beta_s": 40.0,
            "mb": 480.0,
            "mc": 480.0,
            "m1": 0.0,
            "m2": 0.0,
            "m3": 0.0,
            "m4": 0.0,
            "mg": 900.0,
            "ms": 600.0,
            "mw": 136.8,
            "ma": 7.2,
            "alpha": 1.5,
            "batch_volume": 15.0,
            "workability_binder_delta": -10.0,
            "workability_sand_ratio_delta": -1.0,
            "workability_alpha_delta": 0.0,
            "delta_wb": 0.015,
            "delta_bs": 1.5,
            "strength0": None,
            "strength_p": None,
            "strength_n": None,
            "target_strength": None,
            "wb_adj": None,
            "mb_adj": None,
            "sand_ratio_adj": None,
            "alpha_adj": None,
            "measured_density": None,
        }

        expected = legacy_trial(payload)
        actual = calc_hpc_trial(**payload)
        self.assert_nested_equal(actual, expected)

    def test_workability_sand_ratio_preserves_total_aggregate(self):
        """工作性实验调整砂率时，应保持粗细骨料总量不变。"""
        payload = {
            "wb": 0.3125,
            "beta_s": 43.5,
            "mb": 520.0,
            "mc": 312.0,
            "m1": 104.0,
            "m2": 72.8,
            "m3": 15.6,
            "m4": 15.6,
            "mg": 845.0,
            "ms": 651.46,
            "mw": 162.5,
            "ma": 8.32,
            "alpha": 1.6,
            "batch_volume": 20.0,
            "workability_binder_delta": 0.0,
            "workability_sand_ratio_delta": 1.5,
            "workability_alpha_delta": 0.0,
            "delta_wb": 0.02,
            "delta_bs": 2.0,
            "strength0": None,
            "strength_p": None,
            "strength_n": None,
            "target_strength": None,
            "wb_adj": None,
            "mb_adj": None,
            "sand_ratio_adj": None,
            "alpha_adj": None,
            "measured_density": None,
        }

        actual = calc_hpc_trial(**payload)
        workability_result = actual["workability_result"]
        expected_total_aggregate = js_round(payload["mg"] + payload["ms"], 2)

        self.assertAlmostEqual(
            workability_result["mg"] + workability_result["ms"],
            expected_total_aggregate,
            places=9,
        )
        self.assertAlmostEqual(workability_result["bs"], 45.0, places=9)
        self.assertAlmostEqual(workability_result["ms"], js_round(expected_total_aggregate * 0.45, 2), places=9)
        self.assertAlmostEqual(workability_result["mg"], js_round(expected_total_aggregate * 0.55, 2), places=9)


if __name__ == "__main__":
    unittest.main()