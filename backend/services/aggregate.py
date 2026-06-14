"""
粗细骨料用量计算引擎
====================
公式：
    m_g = V_g × ρ_g
    m_s = βs / (1 - βs) × m_g

参考脚本：粗细骨料用量.py
"""


# 粗骨料绝对体积用量参考表（JGJ 55），供前端展示或查询使用
VG_TABLE = {
    "SF0": {"描述": "坍落度 180~220mm",  "范围": (0.37, 0.40)},
    "SF1": {"描述": "扩展度 500~600mm",  "范围": (0.35, 0.38)},
    "SF2": {"描述": "扩展度 600~700mm",  "范围": (0.32, 0.36)},
    "SF3": {"描述": "扩展度 700~800mm",  "范围": (0.30, 0.32)},
}


def calculate_coarse_aggregate(V_g: float, rho_g: float) -> float:
    """
    计算粗骨料用量 m_g

    参数:
        V_g   : 粗骨料绝对体积用量 (m³)
        rho_g : 粗骨料表观密度 (kg/m³)

    返回:
        m_g : 粗骨料用量 (kg)
    """
    if V_g <= 0:
        raise ValueError(f"粗骨料体积 V_g={V_g} 应大于 0")
    if rho_g <= 0:
        raise ValueError(f"粗骨料密度 rho_g={rho_g} 应大于 0")
    return round(V_g * rho_g, 4)


def calculate_fine_aggregate(m_g: float, beta_s: float) -> float:
    """
    计算细骨料用量 m_s

    参数:
        m_g    : 粗骨料用量 (kg)
        beta_s : 砂率（小数，范围 0~1，不含端点）
                 例如：0.35 表示 35%

    返回:
        m_s : 细骨料用量 (kg)
    """
    if not (0 < beta_s < 1):
        raise ValueError(f"砂率 βs={beta_s} 应为 0~1 之间的小数（不含端点）")
    return round(beta_s / (1 - beta_s) * m_g, 4)


# ── API 服务层封装 ────────────────────────────────────────────────────────────

def calc_aggregate(vg: float, rhog: float, beta_s: float, rhos: float) -> dict:
    """
    粗细骨料用量完整计算（供 API 路由调用）

    参数:
        vg     : 粗骨料绝对体积用量 V_g (m³)
        rhog   : 粗骨料表观密度 ρ_g (kg/m³)
        beta_s : 砂率（小数 0~1）
        rhos   : 细骨料表观密度 ρ_s (kg/m³)，保留参数供后续体积验证使用

    返回:
        {"mg": float, "ms": float}
    """
    mg = calculate_coarse_aggregate(vg, rhog)
    ms = calculate_fine_aggregate(mg, beta_s)
    return {"mg": mg, "ms": ms}
