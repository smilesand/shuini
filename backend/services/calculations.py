"""
services/calculations.py
=========================
服务层入口：导入各服务模块并统一导出，路由层无需改动。

服务模块：
    services/water_binder.py     - 水胶比计算
    services/regression.py       - 回归系数拟合（多模型自动选优）
    services/aggregate.py        - 粗细骨料用量计算
    services/binder.py           - 胶凝材料计算
    services/water_admixture.py  - 水和外加剂计算
    services/uhpc.py             - 超高性能混凝土统一计算
    services/hpc_trial.py        - 高性能试配统一计算
"""

from .water_binder import calc_water_binder
from .regression import fit_regression_coefficients
from .aggregate import calc_aggregate
from .binder import calc_binder
from .water_admixture import calc_water_admixture
from .uhpc import calc_uhpc_mix
from .hpc_trial import calc_hpc_trial
from .uhpc_trial import calc_uhpc_trial

__all__ = [
    "calc_water_binder",
    "fit_regression_coefficients",
    "calc_aggregate",
    "calc_binder",
    "calc_water_admixture",
    "calc_uhpc_mix",
    "calc_hpc_trial",
    "calc_uhpc_trial",
]

