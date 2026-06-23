/**
 * calc/waterAdmixture.ts
 * ======================
 * 水与外加剂用量计算引擎，由后端 services/water_admixture.py 迁移而来。
 *
 * 公式：
 *   mw = mb × (W/B)
 *   ma = mb × α
 *
 * 注意：入参 alpha 为百分比（如 1.0 表示 1%），内部自动转为小数。
 */
import { pyRound } from './rounding'

export interface WaterAdmixtureInput {
  mb: number // 胶凝材料用量 (kg)
  wb: number // 水胶比 W/B
  alpha: number // 外加剂掺量 (%)
}

export interface WaterAdmixtureResult {
  mw: number // 用水量 (kg)
  ma: number // 外加剂用量 (kg)
}

/** 计算用水量 mw = mb × W/B。 */
export function calculateWaterAmount(mb: number, wb: number): number {
  if (mb <= 0) throw new Error(`胶凝材料用量 mb=${mb} 应大于 0`)
  if (wb <= 0) throw new Error(`水胶比 W/B=${wb} 应大于 0`)
  return pyRound(mb * wb, 4)
}

/** 计算外加剂用量 ma = mb × α（α 为小数）。 */
export function calculateAdmixtureAmount(mb: number, alpha: number): number {
  if (alpha < 0) throw new Error(`外加剂掺量 α=${alpha} 不能为负数`)
  return pyRound(mb * alpha, 4)
}

/** 水与外加剂完整计算入口，输出与后端 calc_water_admixture 一致。 */
export function calcWaterAdmixture(input: WaterAdmixtureInput): WaterAdmixtureResult {
  const mw = calculateWaterAmount(input.mb, input.wb)
  const ma = calculateAdmixtureAmount(input.mb, input.alpha / 100.0)
  return { mw, ma }
}
