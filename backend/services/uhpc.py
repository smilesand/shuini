"""
超高性能混凝土统一计算服务
========================
将 PDF / PPT 中 4.5.1~4.5.7、4.7.1 的设计公式集中到服务端，
前端仅负责收集输入、展示结果和保存记录。
"""

from __future__ import annotations

import math


DEFAULT_ASSUMED_MIX_MASS = 2500.0
DEFAULT_STEEL_FIBER_DENSITY = 7850.0


def _round_js(value: float, digits: int = 4) -> float:
    """使用接近前端 Math.round 的舍入策略，避免跨端口径偏差。"""
    factor = 10 ** digits
    return math.floor(value * factor + 0.5) / factor


def _packing_fraction(
    particle_size: float,
    max_particle_size: float,
    min_particle_size: float,
    distribution_index: float,
) -> float:
    denominator = (max_particle_size ** distribution_index) - (min_particle_size ** distribution_index)
    if denominator <= 0:
        raise ValueError("粒径上限必须大于粒径下限")
    if particle_size <= min_particle_size:
        raise ValueError("参与计算的粒径必须大于体系最小粒径")

    numerator = (particle_size ** distribution_index) - (min_particle_size ** distribution_index)
    return (numerator / denominator) * 100.0


def _build_ratio_result(cement: float, fly_ash: float, micro_bead: float, silica_fume: float, digits: int = 2) -> dict:
    return {
        "cement": _round_js(cement, digits),
        "fly_ash": _round_js(fly_ash, digits),
        "micro_bead": _round_js(micro_bead, digits),
        "silica_fume": _round_js(silica_fume, digits),
    }


def calc_uhpc_mix(
    strength_grade: float,
    water_binder_ratio: float,
    admixture_ratio: float,
    sand_binder_ratio: float,
    steel_fiber_volume_ratio: float,
    max_particle_size: float,
    min_particle_size: float,
    distribution_index: float,
    fly_ash_peak_size: float,
    fly_ash_accumulation_size: float,
    micro_bead_peak_size: float,
    micro_bead_silica_fume_ratio: float,
    cement_density: float,
    fly_ash_density: float,
    micro_bead_density: float,
    silica_fume_density: float,
    micro_powder_coefficient: float,
    assumed_mix_mass: float = DEFAULT_ASSUMED_MIX_MASS,
    steel_fiber_density: float = DEFAULT_STEEL_FIBER_DENSITY,
) -> dict:
    """按 UHPC 设计公式计算胶凝材料比例和每方材料用量。"""
    if strength_grade <= 0:
        raise ValueError("强度等级必须大于 0")
    if water_binder_ratio <= 0:
        raise ValueError("水胶比必须大于 0")
    if sand_binder_ratio <= 0:
        raise ValueError("砂胶比必须大于 0")
    if not 0 <= admixture_ratio < 100:
        raise ValueError("外加剂掺量必须在 0~100% 之间")
    if not 0 <= steel_fiber_volume_ratio < 100:
        raise ValueError("钢纤维体积掺量必须在 0~100% 之间")
    if max_particle_size <= min_particle_size:
        raise ValueError("体系最大粒径必须大于体系最小粒径")
    if distribution_index <= 0:
        raise ValueError("粒径分布指数必须大于 0")
    if fly_ash_peak_size <= 0 or fly_ash_accumulation_size <= 0 or micro_bead_peak_size <= 0:
        raise ValueError("峰值粒径和堆积粒径必须大于 0")
    if fly_ash_peak_size - fly_ash_accumulation_size <= min_particle_size:
        raise ValueError("粉煤灰峰值粒径减堆积粒径后必须大于体系最小粒径")
    if not 0 < micro_bead_silica_fume_ratio < 1:
        raise ValueError("微珠占硅灰、微粉的比例必须在 0~1 之间")
    if cement_density <= 0 or fly_ash_density <= 0 or micro_bead_density <= 0 or silica_fume_density <= 0:
        raise ValueError("材料密度必须大于 0")
    if micro_powder_coefficient <= 0:
        raise ValueError("微粉系数必须大于 0")
    if assumed_mix_mass <= 0:
        raise ValueError("假定拌合物质量必须大于 0")
    if steel_fiber_density <= 0:
        raise ValueError("钢纤维密度必须大于 0")

    design_strength = strength_grade * 1.1

    fly_ash_volume_ratio = (
        _packing_fraction(
            fly_ash_peak_size + fly_ash_accumulation_size,
            max_particle_size,
            min_particle_size,
            distribution_index,
        )
        - _packing_fraction(
            fly_ash_peak_size - fly_ash_accumulation_size,
            max_particle_size,
            min_particle_size,
            distribution_index,
        )
    )
    micro_powder_volume_ratio = _packing_fraction(
        micro_bead_peak_size,
        max_particle_size,
        min_particle_size,
        distribution_index,
    )
    micro_bead_volume_ratio = micro_powder_volume_ratio * micro_bead_silica_fume_ratio
    silica_fume_volume_ratio = micro_powder_volume_ratio * (1.0 - micro_bead_silica_fume_ratio)
    cement_volume_ratio = 100.0 - fly_ash_volume_ratio - micro_bead_volume_ratio - silica_fume_volume_ratio

    if cement_volume_ratio <= 0:
        raise ValueError("计算后的水泥体积比例不合法，请检查粒径参数")

    mass_ratio_denominator = (
        cement_volume_ratio * cement_density
        + fly_ash_volume_ratio * fly_ash_density
        + micro_bead_volume_ratio * micro_bead_density
        + silica_fume_volume_ratio * silica_fume_density
    )
    if mass_ratio_denominator <= 0:
        raise ValueError("胶凝材料质量比例分母必须大于 0")

    initial_cement_mass_ratio = (cement_volume_ratio * cement_density / mass_ratio_denominator) * 100.0
    initial_fly_ash_mass_ratio = (fly_ash_volume_ratio * fly_ash_density / mass_ratio_denominator) * 100.0
    initial_micro_bead_mass_ratio = (micro_bead_volume_ratio * micro_bead_density / mass_ratio_denominator) * 100.0
    initial_silica_fume_mass_ratio = (silica_fume_volume_ratio * silica_fume_density / mass_ratio_denominator) * 100.0

    corrected_silica_fume_mass_ratio = initial_silica_fume_mass_ratio * micro_powder_coefficient
    corrected_micro_bead_mass_ratio = initial_micro_bead_mass_ratio * micro_powder_coefficient
    corrected_cement_mass_ratio = (
        initial_cement_mass_ratio
        + initial_silica_fume_mass_ratio
        - corrected_silica_fume_mass_ratio
        + initial_micro_bead_mass_ratio
        - corrected_micro_bead_mass_ratio
    )

    if corrected_cement_mass_ratio <= 0:
        raise ValueError("修正后的水泥质量比例不合法，请检查微粉系数")

    steel_fiber_mass = (steel_fiber_volume_ratio / 100.0) * steel_fiber_density
    alpha_fraction = admixture_ratio / 100.0
    binder_mass = (assumed_mix_mass - steel_fiber_mass) / (1.0 + sand_binder_ratio + water_binder_ratio + alpha_fraction)

    if binder_mass <= 0:
        raise ValueError("计算得到的胶凝材料总量不合法，请检查钢纤维体积掺量或总质量")

    sand_mass = binder_mass * sand_binder_ratio
    water_mass = binder_mass * water_binder_ratio
    admixture_mass = binder_mass * alpha_fraction
    cement_mass = binder_mass * (corrected_cement_mass_ratio / 100.0)
    fly_ash_mass = binder_mass * (initial_fly_ash_mass_ratio / 100.0)
    micro_bead_mass = binder_mass * (corrected_micro_bead_mass_ratio / 100.0)
    silica_fume_mass = binder_mass * (corrected_silica_fume_mass_ratio / 100.0)
    total_mass = binder_mass + sand_mass + water_mass + admixture_mass + steel_fiber_mass

    return {
        "design_strength": _round_js(design_strength, 2),
        "assumed_mix_mass": _round_js(assumed_mix_mass, 2),
        "steel_fiber_density": _round_js(steel_fiber_density, 2),
        "binder_volume_ratios": _build_ratio_result(
            cement=cement_volume_ratio,
            fly_ash=fly_ash_volume_ratio,
            micro_bead=micro_bead_volume_ratio,
            silica_fume=silica_fume_volume_ratio,
        ),
        "binder_mass_ratios": {
            "initial": _build_ratio_result(
                cement=initial_cement_mass_ratio,
                fly_ash=initial_fly_ash_mass_ratio,
                micro_bead=initial_micro_bead_mass_ratio,
                silica_fume=initial_silica_fume_mass_ratio,
            ),
            "corrected": _build_ratio_result(
                cement=corrected_cement_mass_ratio,
                fly_ash=initial_fly_ash_mass_ratio,
                micro_bead=corrected_micro_bead_mass_ratio,
                silica_fume=corrected_silica_fume_mass_ratio,
            ),
        },
        "material_masses": {
            "binder": _round_js(binder_mass, 2),
            "cement": _round_js(cement_mass, 2),
            "fly_ash": _round_js(fly_ash_mass, 2),
            "micro_bead": _round_js(micro_bead_mass, 2),
            "silica_fume": _round_js(silica_fume_mass, 2),
            "sand": _round_js(sand_mass, 2),
            "steel_fiber": _round_js(steel_fiber_mass, 2),
            "water": _round_js(water_mass, 2),
            "admixture": _round_js(admixture_mass, 2),
            "total": _round_js(total_mass, 2),
        },
    }