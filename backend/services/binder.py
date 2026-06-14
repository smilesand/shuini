"""
胶凝材料计算引擎
================
公式：
    βc  = 1 - β₁ - β₂ - β₃ - β₄
    ρb  = 1 / (β₁/ρ₁ + β₂/ρ₂ + β₃/ρ₃ + β₄/ρ₄ + βc/ρc)
    Vp  = 1 - mg/ρg - ms/ρs
    mb  = (Vp - Va) / (1/ρb + W/B / ρw)
    mᵢ  = mb × βᵢ

参考脚本：胶凝材料.py
"""


def calculate_binder_density(
    rho_1: float, beta_1: float,
    rho_2: float, beta_2: float,
    rho_3: float, beta_3: float,
    rho_4: float, beta_4: float,
    rho_c: float,
) -> tuple[float, float]:
    """
    计算胶凝材料表观密度 ρb 及水泥质量分数 βc

    参数:
        rho_1, beta_1 : 粉煤灰密度 (kg/m³)、质量分数（小数）
        rho_2, beta_2 : 矿粉密度   (kg/m³)、质量分数（小数）
        rho_3, beta_3 : 微珠密度   (kg/m³)、质量分数（小数）
        rho_4, beta_4 : 硅灰密度   (kg/m³)、质量分数（小数）
        rho_c         : 水泥密度   (kg/m³)

    返回:
        (rho_b, beta_c) : 胶凝材料表观密度 (kg/m³)，水泥质量分数（小数）
    """
    beta_c = 1.0 - beta_1 - beta_2 - beta_3 - beta_4
    if beta_c < 0:
        raise ValueError(
            f"各掺合料质量分数之和 {(1 - beta_c) * 100:.2f}% 超过 100%，请检查输入"
        )

    denominator = (
        beta_1 / rho_1
        + beta_2 / rho_2
        + beta_3 / rho_3
        + beta_4 / rho_4
        + beta_c / rho_c
    )
    if denominator <= 0:
        raise ValueError("胶凝材料密度分母为零，请检查密度与质量分数输入")

    rho_b = 1.0 / denominator
    return round(rho_b, 4), round(beta_c, 6)


def calculate_paste_volume(
    m_g: float, rho_g: float,
    m_s: float, rho_s: float,
) -> float:
    """
    计算浆体体积 Vp

    参数:
        m_g   : 粗骨料用量 (kg)
        rho_g : 粗骨料表观密度 (kg/m³)
        m_s   : 细骨料用量 (kg)
        rho_s : 细骨料表观密度 (kg/m³)

    返回:
        Vp : 浆体体积 (m³)
    """
    vp = 1.0 - m_g / rho_g - m_s / rho_s
    return round(vp, 8)


def calculate_binder_amount(
    Vp: float,
    Va: float,
    rho_b: float,
    WB_ratio: float,
    rho_w: float = 1000.0,
) -> float:
    """
    计算胶凝材料用量 mb

    参数:
        Vp       : 浆体体积 (m³)
        Va       : 含气量体积 (m³)，例如 0.01
        rho_b    : 胶凝材料表观密度 (kg/m³)
        WB_ratio : 水胶比 W/B
        rho_w    : 水的密度 (kg/m³)，默认 1000

    返回:
        mb : 胶凝材料用量 (kg)
    """
    if Vp <= Va:
        raise ValueError(
            f"浆体体积 Vp={Vp:.6f} ≤ 含气量 Va={Va}，请检查骨料参数"
        )

    denominator = 1.0 / rho_b + WB_ratio / rho_w
    if denominator <= 0:
        raise ValueError("胶凝材料用量分母为零，请检查水胶比和密度输入")

    mb = (Vp - Va) / denominator
    return round(mb, 4)


def calculate_component_amounts(
    mb: float,
    beta_1: float,
    beta_2: float,
    beta_3: float,
    beta_4: float,
    beta_c: float,
) -> dict:
    """
    计算各胶凝组分用量

    参数:
        mb              : 胶凝材料总用量 (kg)
        beta_1..beta_4  : 粉煤灰、矿粉、微珠、硅灰质量分数（小数）
        beta_c          : 水泥质量分数（小数）

    返回:
        各组分用量字典 (kg)
    """
    return {
        "m1": round(mb * beta_1, 4),  # 粉煤灰
        "m2": round(mb * beta_2, 4),  # 矿粉
        "m3": round(mb * beta_3, 4),  # 微珠
        "m4": round(mb * beta_4, 4),  # 硅灰
        "mc": round(mb * beta_c, 4),  # 水泥
    }


# ── API 服务层封装 ────────────────────────────────────────────────────────────

def calc_binder(
    b1p: float, rho1: float,
    b2p: float, rho2: float,
    b3p: float, rho3: float,
    b4p: float, rho4: float,
    rhoc: float,
    va: float,
    mg: float, ms: float,
    rhog: float, rhos: float,
    wb: float,
    rho_w: float = 1000.0,
) -> dict:
    """
    胶凝材料完整计算（供 API 路由调用）

    参数（掺合料质量分数 b*p 为百分比，内部转换为小数）:
        b1p..b4p : 粉煤灰/矿粉/微珠/硅灰质量分数 (%)
        rho1~4   : 对应密度 (kg/m³)
        rhoc     : 水泥密度 (kg/m³)
        va       : 含气量 (m³)
        mg, ms   : 粗/细骨料用量 (kg)
        rhog,rhos: 粗/细骨料密度 (kg/m³)
        wb       : 水胶比
        rho_w    : 水密度 (kg/m³)

    返回:
        {bc, rhob, vp, mb, m1, m2, m3, m4, mc}
    """
    b1 = b1p / 100.0
    b2 = b2p / 100.0
    b3 = b3p / 100.0
    b4 = b4p / 100.0

    rho_b, bc = calculate_binder_density(rho1, b1, rho2, b2, rho3, b3, rho4, b4, rhoc)
    vp        = calculate_paste_volume(mg, rhog, ms, rhos)
    mb        = calculate_binder_amount(vp, va, rho_b, wb, rho_w)
    parts     = calculate_component_amounts(mb, b1, b2, b3, b4, bc)

    return {
        "bc":   round(bc,    6),
        "rhob": round(rho_b, 4),
        "vp":   round(vp,    8),
        "mb":   round(mb,    4),
        **parts,
    }
