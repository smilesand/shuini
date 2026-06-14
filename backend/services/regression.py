"""
回归系数拟合引擎
================
参考脚本：回归系数拟合.py

策略：依次尝试三个候选模型，按 R² 提升阈值自动选择最优模型，
      最终将模型系数转换为鲍罗米公式标准回归系数 αa、αb、αc。

候选模型：
    模型1 : z = a·xy + b·y          (最简单)
    模型2 : z = a·xy + b·y + c       (带截距)
    模型3 : z = a·xy + b·y + c·y² + d (二次项，最复杂)

α 系数换算（适用于模型1/2）：
    αa =  a
    αb = -b / a
    αc = -c   (模型1 时 αc = 0)

输入数据格式（CSV 文本）：
    每行 3 列：胶水比(x), 胶材强度fb(y), 混凝土强度fcu(z)
"""

import io
import csv

import numpy as np


# ── 内部工具函数 ──────────────────────────────────────────────────────────────

def _parse_csv(csv_text: str):
    """
    解析 CSV 文本，返回 (x, y, z) numpy 数组
    自动跳过无法转换为数字的行（表头等）
    """
    reader = csv.reader(io.StringIO(csv_text.strip()))
    rows = []
    for line in reader:
        if len(line) < 3:
            continue
        try:
            row = [float(v.strip()) for v in line[:3]]
            rows.append(row)
        except ValueError:
            continue

    if len(rows) < 3:
        raise ValueError(f"有效数据行不足（当前 {len(rows)} 行），至少需要 3 行")

    data = np.array(rows)
    return data[:, 0], data[:, 1], data[:, 2]


def _lstsq_fit(X: np.ndarray, z: np.ndarray):
    """
    最小二乘拟合，返回 (coefficients, R²)
    等价于 sklearn.LinearRegression(fit_intercept=False)
    """
    coeffs, _, _, _ = np.linalg.lstsq(X, z, rcond=None)
    z_pred = X @ coeffs
    ss_res = float(np.sum((z - z_pred) ** 2))
    ss_tot = float(np.sum((z - z.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return coeffs, round(r2, 6)


def _fit_all_models(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> list[dict]:
    """
    对同一组数据拟合三个候选模型，返回各模型的系数和 R²
    """
    xy   = x * y
    ones = np.ones_like(x)

    # 模型1: z = a·xy + b·y
    c1, r2_1 = _lstsq_fit(np.column_stack([xy, y]), z)

    # 模型2: z = a·xy + b·y + c
    c2, r2_2 = _lstsq_fit(np.column_stack([xy, y, ones]), z)

    # 模型3: z = a·xy + b·y + c·y² + d
    c3, r2_3 = _lstsq_fit(np.column_stack([xy, y, y ** 2, ones]), z)

    return [
        {"name": "model1", "label": "z=a·xy+b·y",          "coeffs": c1, "r2": r2_1},
        {"name": "model2", "label": "z=a·xy+b·y+c",        "coeffs": c2, "r2": r2_2},
        {"name": "model3", "label": "z=a·xy+b·y+c·y²+d",   "coeffs": c3, "r2": r2_3},
    ]


def _select_best_model(models: list[dict], threshold: float = 0.001) -> dict:
    """
    从最简单模型开始，若后一模型 R² 提升超过阈值则升级，否则保留当前。
    与参考脚本 select_model() 逻辑完全一致。
    """
    best = models[0]
    for m in models[1:]:
        if m["r2"] - best["r2"] > threshold:
            best = m
        else:
            break
    return best


def _extract_alpha(
    model: dict,
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
) -> tuple[float, float, float]:
    """
    将模型系数转换为鲍罗米公式的 αa, αb, αc。

    模型3 因含 y² 项无法直接转换，退化为模型2 重新拟合后再提取。
    （与参考脚本 compute_alpha() 逻辑一致）
    """
    name   = model["name"]
    coeffs = model["coeffs"]

    if name == "model1":
        a, b = float(coeffs[0]), float(coeffs[1])
        return a, -b / a, 0.0

    elif name == "model2":
        a, b, c = float(coeffs[0]), float(coeffs[1]), float(coeffs[2])
        return a, -b / a, -c

    else:  # model3 → 退化为 model2
        xy   = x * y
        ones = np.ones_like(x)
        c2, _ = _lstsq_fit(np.column_stack([xy, y, ones]), z)
        a, b, c = float(c2[0]), float(c2[1]), float(c2[2])
        return a, -b / a, -c


# ── API 服务层封装 ────────────────────────────────────────────────────────────

def fit_regression_coefficients(csv_text: str) -> dict:
    """
    从 CSV 文本拟合鲍罗米公式回归系数

    输入格式（每行 3 列，无需表头，含表头会自动跳过）：
        胶水比, 胶材28d强度(MPa), 混凝土28d强度(MPa)

    返回:
        {
            "aa": float,   # αa
            "ab": float,   # αb
            "ac": float,   # αc
            "r2": float,   # 所选模型决定系数
        }
    """
    x, y, z = _parse_csv(csv_text)
    models   = _fit_all_models(x, y, z)
    best     = _select_best_model(models)
    aa, ab, ac = _extract_alpha(best, x, y, z)

    return {
        "aa": round(aa, 6),
        "ab": round(ab, 6),
        "ac": round(ac, 6),
        "r2": round(float(best["r2"]), 6),
    }
