/**
 * calc/waterBinder.ts
 * ===================
 * 水胶比计算引擎（鲍罗米公式），由后端 services/water_binder.py 迁移而来。
 *
 * 公式：
 *   f_cu,0 = f_cu,k × 1.15
 *   W/B    = αa × fb / (f_cu,0 + αa × αb × fb + αc)
 */
import { pyRound } from './rounding'

export interface WaterBinderInput {
  fcuk: number // 强度等级 f_cu,k (MPa)
  fb: number // 胶材 28d 强度 fb (MPa)
  aa?: number // 回归系数 αa，默认 0.33
  ab?: number // 回归系数 αb，默认 1.09
  ac?: number // 回归系数 αc，默认 -49.54
}

export interface WaterBinderResult {
  fcu0: number // 配制强度 f_cu,0 (MPa)
  wb: number // 水胶比 W/B
}

/** 计算配制强度 f_cu,0 = f_cu,k × 1.15。 */
export function calculateFcu0(fcuk: number): number {
  return pyRound(fcuk * 1.15, 4)
}

/** 计算水胶比 W/B，对非法分母与超界结果抛出与后端一致的错误。 */
export function calculateWaterBinderRatio(
  fcu0: number,
  fb: number,
  alphaA = 0.33,
  alphaB = 1.09,
  alphaC = -49.54,
): number {
  const numerator = alphaA * fb
  const denominator = fcu0 + alphaA * alphaB * fb + alphaC

  if (denominator <= 0) {
    throw new Error(`分母非正（${denominator.toFixed(4)}），请检查回归系数和强度参数`)
  }

  const wb = numerator / denominator

  if (!(wb > 0 && wb < 2)) {
    throw new Error(`计算所得水胶比 ${wb.toFixed(4)} 超出合理范围（0~2），请检查输入参数`)
  }

  return pyRound(wb, 6)
}

/** 水胶比完整计算入口，输出与后端 calc_water_binder 一致。 */
export function calcWaterBinder(input: WaterBinderInput): WaterBinderResult {
  const { fcuk, fb, aa = 0.33, ab = 1.09, ac = -49.54 } = input
  const fcu0 = calculateFcu0(fcuk)
  const wb = calculateWaterBinderRatio(fcu0, fb, aa, ab, ac)
  return { fcu0, wb }
}
