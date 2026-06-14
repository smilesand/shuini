"""UHPC 统一计算服务回归测试。"""

from __future__ import annotations

import math
import unittest

from services.uhpc import calc_uhpc_mix


def js_round(value: float, digits: int = 4) -> float:
    factor = 10 ** digits
    return math.floor(value * factor + 0.5) / factor


def packing_fraction(particle_size: float, max_particle_size: float, min_particle_size: float, distribution_index: float) -> float:
    return ((particle_size ** distribution_index - min_particle_size ** distribution_index) / (max_particle_size ** distribution_index - min_particle_size ** distribution_index)) * 100.0


def build_expected(payload: dict[str, float]) -> dict:
    fly_ash_volume_ratio = (
        packing_fraction(
            payload["fly_ash_peak_size"] + payload["fly_ash_accumulation_size"],
            payload["max_particle_size"],
            payload["min_particle_size"],
            payload["distribution_index"],
        )
        - packing_fraction(
            payload["fly_ash_peak_size"] - payload["fly_ash_accumulation_size"],
            payload["max_particle_size"],
            payload["min_particle_size"],
            payload["distribution_index"],
        )
    )
    micro_powder_volume_ratio = packing_fraction(
        payload["micro_bead_peak_size"],
        payload["max_particle_size"],
        payload["min_particle_size"],
        payload["distribution_index"],
    )
    micro_bead_volume_ratio = micro_powder_volume_ratio * payload["micro_bead_silica_fume_ratio"]
    silica_fume_volume_ratio = micro_powder_volume_ratio * (1.0 - payload["micro_bead_silica_fume_ratio"])
    cement_volume_ratio = 100.0 - fly_ash_volume_ratio - micro_bead_volume_ratio - silica_fume_volume_ratio

    denominator = (
        cement_volume_ratio * payload["cement_density"]
        + fly_ash_volume_ratio * payload["fly_ash_density"]
        + micro_bead_volume_ratio * payload["micro_bead_density"]
        + silica_fume_volume_ratio * payload["silica_fume_density"]
    )

    initial_cement = (cement_volume_ratio * payload["cement_density"] / denominator) * 100.0
    initial_fly_ash = (fly_ash_volume_ratio * payload["fly_ash_density"] / denominator) * 100.0
    initial_micro_bead = (micro_bead_volume_ratio * payload["micro_bead_density"] / denominator) * 100.0
    initial_silica_fume = (silica_fume_volume_ratio * payload["silica_fume_density"] / denominator) * 100.0

    corrected_silica_fume = initial_silica_fume * payload["micro_powder_coefficient"]
    corrected_micro_bead = initial_micro_bead * payload["micro_powder_coefficient"]
    corrected_cement = (
        initial_cement
        + initial_silica_fume
        - corrected_silica_fume
        + initial_micro_bead
        - corrected_micro_bead
    )

    steel_fiber_mass = (payload["steel_fiber_volume_ratio"] / 100.0) * payload["steel_fiber_density"]
    alpha_fraction = payload["admixture_ratio"] / 100.0
    binder_mass = (payload["assumed_mix_mass"] - steel_fiber_mass) / (
        1.0 + payload["sand_binder_ratio"] + payload["water_binder_ratio"] + alpha_fraction
    )

    return {
        "design_strength": js_round(payload["strength_grade"] * 1.1, 2),
        "binder_volume_ratios": {
            "cement": js_round(cement_volume_ratio, 2),
            "fly_ash": js_round(fly_ash_volume_ratio, 2),
            "micro_bead": js_round(micro_bead_volume_ratio, 2),
            "silica_fume": js_round(silica_fume_volume_ratio, 2),
        },
        "binder_mass_ratios": {
            "initial": {
                "cement": js_round(initial_cement, 2),
                "fly_ash": js_round(initial_fly_ash, 2),
                "micro_bead": js_round(initial_micro_bead, 2),
                "silica_fume": js_round(initial_silica_fume, 2),
            },
            "corrected": {
                "cement": js_round(corrected_cement, 2),
                "fly_ash": js_round(initial_fly_ash, 2),
                "micro_bead": js_round(corrected_micro_bead, 2),
                "silica_fume": js_round(corrected_silica_fume, 2),
            },
        },
        "material_masses": {
            "binder": js_round(binder_mass, 2),
            "cement": js_round(binder_mass * corrected_cement / 100.0, 2),
            "fly_ash": js_round(binder_mass * initial_fly_ash / 100.0, 2),
            "micro_bead": js_round(binder_mass * corrected_micro_bead / 100.0, 2),
            "silica_fume": js_round(binder_mass * corrected_silica_fume / 100.0, 2),
            "sand": js_round(binder_mass * payload["sand_binder_ratio"], 2),
            "steel_fiber": js_round(steel_fiber_mass, 2),
            "water": js_round(binder_mass * payload["water_binder_ratio"], 2),
            "admixture": js_round(binder_mass * alpha_fraction, 2),
            "total": js_round(
                binder_mass
                + binder_mass * payload["sand_binder_ratio"]
                + binder_mass * payload["water_binder_ratio"]
                + binder_mass * alpha_fraction
                + steel_fiber_mass,
                2,
            ),
        },
    }


class UhpcMixServiceTest(unittest.TestCase):
    def test_calc_uhpc_mix_matches_formula_baseline(self) -> None:
        payload = {
            "strength_grade": 130.0,
            "water_binder_ratio": 0.19,
            "admixture_ratio": 1.8,
            "sand_binder_ratio": 1.2,
            "steel_fiber_volume_ratio": 1.8,
            "max_particle_size": 80.0,
            "min_particle_size": 1.0,
            "distribution_index": 0.22,
            "fly_ash_peak_size": 18.0,
            "fly_ash_accumulation_size": 8.0,
            "micro_bead_peak_size": 4.0,
            "micro_bead_silica_fume_ratio": 0.5,
            "cement_density": 3100.0,
            "fly_ash_density": 2300.0,
            "micro_bead_density": 2600.0,
            "silica_fume_density": 2200.0,
            "micro_powder_coefficient": 0.55,
            "assumed_mix_mass": 2500.0,
            "steel_fiber_density": 7850.0,
        }

        actual = calc_uhpc_mix(**payload)
        expected = build_expected(payload)

        self.assertEqual(actual["design_strength"], expected["design_strength"])
        self.assertEqual(actual["binder_volume_ratios"], expected["binder_volume_ratios"])
        self.assertEqual(actual["binder_mass_ratios"], expected["binder_mass_ratios"])
        self.assertEqual(actual["material_masses"], expected["material_masses"])
        self.assertEqual(actual["material_masses"]["total"], 2500.0)

    def test_calc_uhpc_mix_rejects_invalid_fly_ash_window(self) -> None:
        with self.assertRaisesRegex(ValueError, "粉煤灰峰值粒径减堆积粒径后必须大于体系最小粒径"):
            calc_uhpc_mix(
                strength_grade=130,
                water_binder_ratio=0.19,
                admixture_ratio=1.8,
                sand_binder_ratio=1.2,
                steel_fiber_volume_ratio=1.8,
                max_particle_size=80,
                min_particle_size=1,
                distribution_index=0.22,
                fly_ash_peak_size=5,
                fly_ash_accumulation_size=4.5,
                micro_bead_peak_size=4,
                micro_bead_silica_fume_ratio=0.5,
                cement_density=3100,
                fly_ash_density=2300,
                micro_bead_density=2600,
                silica_fume_density=2200,
                micro_powder_coefficient=0.55,
                assumed_mix_mass=2500,
                steel_fiber_density=7850,
            )


if __name__ == "__main__":
    unittest.main()