"""
水胶比计算引擎
=============
公式（鲍罗米公式）：
    f_cu,0 = f_cu,k × 1.15
    W/B = αa × fb / (f_cu,0 + αa × αb × fb + αc)

参考脚本：水胶比计算.py
"""


def calculate_fcu0(fcuk: float) -> float:
    """
    计算混凝土配制强度 f_cu,0

    参数:
        fcuk : 混凝土强度标准值 f_cu,k (MPa)

    返回:
        fcu0 : 混凝土配制强度 (MPa)
    """
    return round(fcuk * 1.15, 4)


def calculate_water_binder_ratio(
    fcu0: float,
    fb: float,
    alpha_a: float = 0.33,
    alpha_b: float = 1.09,
    alpha_c: float = -49.54,
) -> float:
    """
    计算水胶比 W/B

    参数:
        fcu0    : 混凝土配制强度 (MPa)
        fb      : 胶材 28d 强度实测值 (MPa)
        alpha_a : 回归系数 αa，默认 0.33
        alpha_b : 回归系数 αb，默认 1.09
        alpha_c : 回归系数 αc，默认 -49.54

    返回:
        水胶比 W/B
    """
    numerator   = alpha_a * fb
    denominator = fcu0 + alpha_a * alpha_b * fb + alpha_c

    if denominator <= 0:
        raise ValueError(
            f"分母非正（{denominator:.4f}），请检查回归系数和强度参数"
        )

    wb = numerator / denominator

    if not (0 < wb < 2):
        raise ValueError(
            f"计算所得水胶比 {wb:.4f} 超出合理范围（0~2），请检查输入参数"
        )

    return round(wb, 6)


# ── API 服务层封装 ────────────────────────────────────────────────────────────

def calc_water_binder(
    fcuk: float,
    fb: float,
    aa: float = 0.33,
    ab: float = 1.09,
    ac: float = -49.54,
) -> dict:
    """
    水胶比完整计算（供 API 路由调用）

    参数:
        fcuk : 强度等级 f_cu,k (MPa)
        fb   : 胶材 28d 强度 (MPa)
        aa   : 回归系数 αa
        ab   : 回归系数 αb
        ac   : 回归系数 αc

    返回:
        {"fcu0": float, "wb": float}
    """
    fcu0 = calculate_fcu0(fcuk)
    wb   = calculate_water_binder_ratio(fcu0, fb, aa, ab, ac)
    return {"fcu0": fcu0, "wb": wb}
