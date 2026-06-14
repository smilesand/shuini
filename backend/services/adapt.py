"""
适配调整计算引擎
================
根据调整后的胶材用量、砂率和外加剂掺量，重新计算试拌配合比。

计算规则（参照 JGJ 55）：
    1. 水泥/粉煤灰/矿粉/微珠/硅灰 = mb_adj × 各自质量分数
    2. 粗骨料不变（Vg 不变）
    3. 细骨料 = β_s_adj / (1 - β_s_adj) × mg（按新砂率重算）
    4. 用水量 = mb_adj × W/B（水胶比不变）
    5. 外加剂 = mb_adj × α_adj
"""


def calc_adapt(
    mb_adj: float,
    beta_s_adj: float,
    alpha_adj: float,
    wb: float,
    bc: float,
    b1: float,
    b2: float,
    b3: float,
    b4: float,
    mg: float,
) -> dict:
    """
    适配调整完整计算

    参数:
        mb_adj    : 调整后胶凝材料总用量 (kg)
        beta_s_adj: 调整后砂率（小数 0~1）
        alpha_adj : 调整后外加剂掺量（小数，例如 0.01 表示 1%）
        wb        : 水胶比（不变）
        bc        : 水泥质量分数（小数）
        b1~b4     : 粉煤灰/矿粉/微珠/硅灰质量分数（小数）
        mg        : 粗骨料用量 (kg)，不变

    返回:
        {mc, m1, m2, m3, m4, mg, ms, mw, ma, mb}
    """
    if mb_adj <= 0:
        raise ValueError(f"调整后胶材用量 mb_adj={mb_adj} 应大于 0")
    if not (0 < beta_s_adj < 1):
        raise ValueError(f"调整后砂率 β_s={beta_s_adj} 应为 0~1 之间的小数（不含端点）")
    if alpha_adj < 0:
        raise ValueError(f"调整后外加剂掺量 α={alpha_adj} 不能为负数")
    if mg <= 0:
        raise ValueError(f"粗骨料用量 mg={mg} 应大于 0")

    mc_adj = round(mb_adj * bc, 4)
    m1_adj = round(mb_adj * b1, 4)
    m2_adj = round(mb_adj * b2, 4)
    m3_adj = round(mb_adj * b3, 4)
    m4_adj = round(mb_adj * b4, 4)

    ms_adj = round(beta_s_adj / (1.0 - beta_s_adj) * mg, 4)

    mw_adj = round(mb_adj * wb, 4)
    ma_adj = round(mb_adj * alpha_adj, 4)

    return {
        "mb": round(mb_adj, 4),
        "mc": mc_adj,
        "m1": m1_adj,
        "m2": m2_adj,
        "m3": m3_adj,
        "m4": m4_adj,
        "mg": round(mg, 4),
        "ms": ms_adj,
        "mw": mw_adj,
        "ma": ma_adj,
    }
