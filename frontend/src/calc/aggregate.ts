/**
 * calc/aggregate.ts
 * =================
 * 粗细骨料用量计算引擎，由后端 services/aggregate.py 迁移而来。
 *
 * 公式：
 *   m_g = V_g × ρ_g
 *   m_s = βs / (1 - βs) × m_g
 */
import { pyRound } from './rounding'

export interface AggregateInput {
  vg: number // 粗骨料绝对体积用量 V_g (m³)
  rhog: number // 粗骨料表观密度 ρ_g (kg/m³)
  beta_s: number // 砂率（小数 0~1，不含端点）
  rhos: number // 细骨料表观密度 ρ_s (kg/m³)，保留供后续体积验证
}

export interface AggregateResult {
  mg: number // 粗骨料用量 (kg)
  ms: number // 细骨料用量 (kg)
}

/** 计算粗骨料用量 m_g = V_g × ρ_g。 */
export function calculateCoarseAggregate(vg: number, rhog: number): number {
  if (vg <= 0) throw new Error(`粗骨料体积 V_g=${vg} 应大于 0`)
  if (rhog <= 0) throw new Error(`粗骨料密度 rho_g=${rhog} 应大于 0`)
  return pyRound(vg * rhog, 4)
}

/** 计算细骨料用量 m_s = βs / (1 - βs) × m_g。 */
export function calculateFineAggregate(mg: number, betaS: number): number {
  if (!(betaS > 0 && betaS < 1)) {
    throw new Error(`砂率 βs=${betaS} 应为 0~1 之间的小数（不含端点）`)
  }
  return pyRound((betaS / (1 - betaS)) * mg, 4)
}

/** 粗细骨料用量完整计算入口，输出与后端 calc_aggregate 一致。 */
export function calcAggregate(input: AggregateInput): AggregateResult {
  const mg = calculateCoarseAggregate(input.vg, input.rhog)
  const ms = calculateFineAggregate(mg, input.beta_s)
  return { mg, ms }
}
