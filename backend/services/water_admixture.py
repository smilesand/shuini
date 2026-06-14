"""
水和外加剂用量计算引擎
======================
公式：
    mw = mb × (W/B)
    ma = mb × α

参考脚本：水和外加剂.py
"""


def calculate_water_amount(mb: float, WB_ratio: float) -> float:
    """
    计算用水量 mw

    参数:
        mb       : 胶凝材料用量 (kg)
        WB_ratio : 水胶比 W/B

    返回:
        mw : 用水量 (kg)
    """
    if mb <= 0:
        raise ValueError(f"胶凝材料用量 mb={mb} 应大于 0")
    if WB_ratio <= 0:
        raise ValueError(f"水胶比 W/B={WB_ratio} 应大于 0")
    return round(mb * WB_ratio, 4)


def calculate_admixture_amount(mb: float, alpha: float) -> float:
    """
    计算外加剂用量 ma

    参数:
        mb    : 胶凝材料用量 (kg)
        alpha : 外加剂掺量（小数，例如 0.01 表示 1%）

    返回:
        ma : 外加剂用量 (kg)
    """
    if alpha < 0:
        raise ValueError(f"外加剂掺量 α={alpha} 不能为负数")
    return round(mb * alpha, 4)


# ── API 服务层封装 ────────────────────────────────────────────────────────────

def calc_water_admixture(mb: float, wb: float, alpha: float) -> dict:
    """
    水和外加剂用量完整计算（供 API 路由调用）

    参数:
        mb    : 胶凝材料用量 (kg)
        wb    : 水胶比 W/B
        alpha : 外加剂掺量（百分比，例如 1.0 表示 1%，内部自动转为小数）

    返回:
        {"mw": float, "ma": float}
    """
    mw = calculate_water_amount(mb, wb)
    ma = calculate_admixture_amount(mb, alpha / 100.0)
    return {"mw": mw, "ma": ma}
