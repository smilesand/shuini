/**
 * calc/binder.ts
 * ==============
 * 胶凝材料计算引擎，由后端 services/binder.py 迁移而来。
 *
 * 公式：
 *   βc  = 1 - β₁ - β₂ - β₃ - β₄
 *   ρb  = 1 / (β₁/ρ₁ + β₂/ρ₂ + β₃/ρ₃ + β₄/ρ₄ + βc/ρc)
 *   Vp  = 1 - mg/ρg - ms/ρs
 *   mb  = (Vp - Va) / (1/ρb + W/B / ρw)
 *   mᵢ  = mb × βᵢ
 *
 * 注意：入参中的掺合料质量分数 b*p 为百分比（如 20 表示 20%），内部转换为小数。
 */
import { pyRound } from './rounding'

export interface BinderInput {
  b1p: number // 粉煤灰质量分数 (%)
  rho1: number // 粉煤灰密度 (kg/m³)
  b2p: number // 矿粉质量分数 (%)
  rho2: number // 矿粉密度 (kg/m³)
  b3p: number // 微珠质量分数 (%)
  rho3: number // 微珠密度 (kg/m³)
  b4p: number // 硅灰质量分数 (%)
  rho4: number // 硅灰密度 (kg/m³)
  rhoc: number // 水泥密度 (kg/m³)
  va: number // 含气量 (m³)
  mg: number // 粗骨料用量 (kg)
  ms: number // 细骨料用量 (kg)
  rhog: number // 粗骨料密度 (kg/m³)
  rhos: number // 细骨料密度 (kg/m³)
  wb: number // 水胶比 W/B
  rhoW?: number // 水密度 (kg/m³)，默认 1000
}

export interface BinderResult {
  bc: number // 水泥质量分数（小数）
  rhob: number // 胶凝材料表观密度 (kg/m³)
  vp: number // 浆体体积 (m³)
  mb: number // 胶凝材料总用量 (kg)
  m1: number // 粉煤灰用量 (kg)
  m2: number // 矿粉用量 (kg)
  m3: number // 微珠用量 (kg)
  m4: number // 硅灰用量 (kg)
  mc: number // 水泥用量 (kg)
}

/** 计算胶凝材料表观密度 ρb 及水泥质量分数 βc。 */
export function calculateBinderDensity(
  rho1: number, beta1: number,
  rho2: number, beta2: number,
  rho3: number, beta3: number,
  rho4: number, beta4: number,
  rhoc: number,
): { rhoB: number; betaC: number } {
  const betaC = 1.0 - beta1 - beta2 - beta3 - beta4
  if (betaC < 0) {
    throw new Error(`各掺合料质量分数之和 ${((1 - betaC) * 100).toFixed(2)}% 超过 100%，请检查输入`)
  }

  const denominator =
    beta1 / rho1 + beta2 / rho2 + beta3 / rho3 + beta4 / rho4 + betaC / rhoc
  if (denominator <= 0) {
    throw new Error('胶凝材料密度分母为零，请检查密度与质量分数输入')
  }

  return { rhoB: pyRound(1.0 / denominator, 4), betaC: pyRound(betaC, 6) }
}

/** 计算浆体体积 Vp = 1 - mg/ρg - ms/ρs。 */
export function calculatePasteVolume(mg: number, rhog: number, ms: number, rhos: number): number {
  return pyRound(1.0 - mg / rhog - ms / rhos, 8)
}

/** 计算胶凝材料用量 mb = (Vp - Va) / (1/ρb + W/B / ρw)。 */
export function calculateBinderAmount(
  vp: number,
  va: number,
  rhoB: number,
  wb: number,
  rhoW = 1000.0,
): number {
  if (vp <= va) {
    throw new Error(`浆体体积 Vp=${vp.toFixed(6)} ≤ 含气量 Va=${va}，请检查骨料参数`)
  }
  const denominator = 1.0 / rhoB + wb / rhoW
  if (denominator <= 0) {
    throw new Error('胶凝材料用量分母为零，请检查水胶比和密度输入')
  }
  return pyRound((vp - va) / denominator, 4)
}

/** 胶凝材料完整计算入口，输出与后端 calc_binder 一致。 */
export function calcBinder(input: BinderInput): BinderResult {
  const b1 = input.b1p / 100.0
  const b2 = input.b2p / 100.0
  const b3 = input.b3p / 100.0
  const b4 = input.b4p / 100.0
  const rhoW = input.rhoW ?? 1000.0

  const { rhoB, betaC } = calculateBinderDensity(
    input.rho1, b1, input.rho2, b2, input.rho3, b3, input.rho4, b4, input.rhoc,
  )
  const vp = calculatePasteVolume(input.mg, input.rhog, input.ms, input.rhos)
  const mb = calculateBinderAmount(vp, input.va, rhoB, input.wb, rhoW)

  return {
    bc: pyRound(betaC, 6),
    rhob: pyRound(rhoB, 4),
    vp: pyRound(vp, 8),
    mb: pyRound(mb, 4),
    m1: pyRound(mb * b1, 4),
    m2: pyRound(mb * b2, 4),
    m3: pyRound(mb * b3, 4),
    m4: pyRound(mb * b4, 4),
    mc: pyRound(mb * betaC, 4),
  }
}
