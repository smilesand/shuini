/**
 * calc/adapt.ts
 * =============
 * 适配调整计算引擎，由后端 services/adapt.py 迁移而来。
 *
 * 根据调整后的胶材用量、砂率和外加剂掺量重新计算试拌配合比（参照 JGJ 55）：
 *   1. 各胶材组分 = mb_adj × 各自质量分数
 *   2. 粗骨料不变（Vg 不变）
 *   3. 细骨料 = β_s_adj / (1 - β_s_adj) × mg
 *   4. 用水量 = mb_adj × W/B（水胶比不变）
 *   5. 外加剂 = mb_adj × α_adj
 *
 * 注意：alpha_adj 在此为「小数」（如 0.01 表示 1%）。后端路由会在调用前将
 * 百分比 /100 转换，前端调用方需保持同样约定。
 */
import { pyRound } from './rounding'

export interface AdaptInput {
  mb_adj: number // 调整后胶凝材料总用量 (kg)
  beta_s_adj: number // 调整后砂率（小数 0~1）
  alpha_adj: number // 调整后外加剂掺量（小数）
  wb: number // 水胶比（不变）
  bc: number // 水泥质量分数（小数）
  b1: number // 粉煤灰质量分数（小数）
  b2: number // 矿粉质量分数（小数）
  b3: number // 微珠质量分数（小数）
  b4: number // 硅灰质量分数（小数）
  mg: number // 粗骨料用量 (kg)，不变
}

export interface AdaptResult {
  mb: number
  mc: number
  m1: number
  m2: number
  m3: number
  m4: number
  mg: number
  ms: number
  mw: number
  ma: number
}

/** 适配调整完整计算，输出与后端 calc_adapt 一致。 */
export function calcAdapt(input: AdaptInput): AdaptResult {
  const { mb_adj, beta_s_adj, alpha_adj, wb, bc, b1, b2, b3, b4, mg } = input

  if (mb_adj <= 0) throw new Error(`调整后胶材用量 mb_adj=${mb_adj} 应大于 0`)
  if (!(beta_s_adj > 0 && beta_s_adj < 1)) {
    throw new Error(`调整后砂率 β_s=${beta_s_adj} 应为 0~1 之间的小数（不含端点）`)
  }
  if (alpha_adj < 0) throw new Error(`调整后外加剂掺量 α=${alpha_adj} 不能为负数`)
  if (mg <= 0) throw new Error(`粗骨料用量 mg=${mg} 应大于 0`)

  return {
    mb: pyRound(mb_adj, 4),
    mc: pyRound(mb_adj * bc, 4),
    m1: pyRound(mb_adj * b1, 4),
    m2: pyRound(mb_adj * b2, 4),
    m3: pyRound(mb_adj * b3, 4),
    m4: pyRound(mb_adj * b4, 4),
    mg: pyRound(mg, 4),
    ms: pyRound((beta_s_adj / (1.0 - beta_s_adj)) * mg, 4),
    mw: pyRound(mb_adj * wb, 4),
    ma: pyRound(mb_adj * alpha_adj, 4),
  }
}
