/**
 * calc/uhpcTrial.ts
 * =================
 * 超高性能（UHPC）试配统一计算引擎，由后端 services/uhpc_trial.py 迁移而来。
 *
 * 三步结构与 HPC 试配一致：
 *   Tab1 试拌配合比 -> Tab2 强度/硅灰变体 + 三点线性回归推荐 -> Tab3 校正配合比 + 密度校正。
 *
 * 舍入：后端 `_round_js` = 银行家舍入后定位小数（等价 pyRound）；
 *       `_truncate_digits` = 朝零截断（truncDigits）。
 */
import { pyRound, truncDigits } from './rounding'
import type {
  UhpcTrialReq,
  UhpcTrialRes,
  UhpcTrialMixRowRes,
} from '../api/calc'

function emptyMix(): UhpcTrialMixRowRes {
  return {
    cement: 0.0,
    fly_ash: 0.0,
    micro_bead: 0.0,
    silica_fume: 0.0,
    sand: 0.0,
    steel_fiber: 0.0,
    water: 0.0,
    admixture: 0.0,
    binder: 0.0,
    total: 0.0,
    admixture_pct: 0.0,
  }
}

/** 核心配合比重算逻辑，与后端 _calc_mix 完全对齐。 */
function calcMix(
  wb: number,
  sb: number,
  alpha: number,
  sfMass: number,
  total: number,
  cementPct: number,
  silicaFumePct: number,
  flyAshPct: number,
  microBeadPct: number,
  sfDelta = 0.0,
  admixOverride: number | null = null,
): UhpcTrialMixRowRes {
  const binder = (total - sfMass) / (1.0 + sb + wb + alpha / 100.0)
  if (binder <= 0) return emptyMix()

  let cePct = cementPct - sfDelta
  let sfPct = silicaFumePct + sfDelta

  // 约束：ce_pct 和 sf_pct 不能为负，超出部分限制在对方身上
  if (sfPct < 0.0) {
    cePct = cementPct + silicaFumePct // 硅灰归零，差值还给水泥
    sfPct = 0.0
  }
  if (cePct < 0.0) {
    sfPct = cementPct + silicaFumePct // 水泥归零，差值还给硅灰
    cePct = 0.0
  }

  const cement = (binder * cePct) / 100.0
  const flyAsh = (binder * flyAshPct) / 100.0
  const microBead = (binder * microBeadPct) / 100.0
  const silicaFume = (binder * sfPct) / 100.0
  const sand = binder * sb
  const waterMass = binder * wb
  const admixture = admixOverride !== null ? admixOverride : (binder * alpha) / 100.0
  const resultTotal = binder * (1.0 + sb + wb) + sfMass + admixture
  const admixturePct = binder > 0 ? (admixture / binder) * 100.0 : 0.0

  return {
    cement: pyRound(cement, 1),
    fly_ash: pyRound(flyAsh, 1),
    micro_bead: pyRound(microBead, 1),
    silica_fume: pyRound(silicaFume, 1),
    sand: pyRound(sand, 1),
    steel_fiber: pyRound(sfMass, 1),
    water: pyRound(waterMass, 1),
    admixture: pyRound(admixture, 1),
    binder: pyRound(binder, 1),
    total: pyRound(resultTotal, 1),
    admixture_pct: pyRound(admixturePct, 2),
  }
}

/** 线性插值，与后端 _lerp 行为对齐（保留以备扩展）。 */
export function lerp(x1: number, y1: number, x2: number, y2: number, tY: number): number {
  if (Math.abs(y2 - y1) < 0.001) return (x1 + x2) / 2.0
  const r = x1 + ((x2 - x1) * (tY - y1)) / (y2 - y1)
  return Math.max(Math.min(r, Math.max(x1, x2)), Math.min(x1, x2))
}

/** 三点最小二乘线性回归，求目标强度 tY 对应的 x（并限制在样本范围内）。 */
function linearFit(
  x1: number, y1: number, x2: number, y2: number, x3: number, y3: number, tY: number,
): number {
  const xs = [x1, x2, x3]
  const ys = [y1, y2, y3]
  const n = 3
  const sumX = xs.reduce((s, v) => s + v, 0)
  const sumY = ys.reduce((s, v) => s + v, 0)
  const sumXy = xs.reduce((s, v, i) => s + v * ys[i], 0)
  const sumX2 = xs.reduce((s, v) => s + v * v, 0)
  const denom = n * sumX2 - sumX * sumX
  if (Math.abs(denom) < 1e-9) return (x1 + x2 + x3) / 3.0
  const a = (n * sumXy - sumX * sumY) / denom
  const b = (sumY - a * sumX) / n
  if (Math.abs(a) < 1e-9) return (x1 + x2 + x3) / 3.0
  const result = (tY - b) / a
  const lo = Math.min(...xs)
  const hi = Math.max(...xs)
  return Math.max(Math.min(result, hi), lo)
}

/** 三点最小二乘线性回归，已知 x 预测 y（如预测外加剂用量）。 */
function linearPredict(
  x1: number, y1: number, x2: number, y2: number, x3: number, y3: number, tX: number,
): number {
  const xs = [x1, x2, x3]
  const ys = [y1, y2, y3]
  const n = 3
  const sumX = xs.reduce((s, v) => s + v, 0)
  const sumY = ys.reduce((s, v) => s + v, 0)
  const sumXy = xs.reduce((s, v, i) => s + v * ys[i], 0)
  const sumX2 = xs.reduce((s, v) => s + v * v, 0)
  const denom = n * sumX2 - sumX * sumX
  if (Math.abs(denom) < 1e-9) return (y1 + y2 + y3) / 3.0
  const a = (n * sumXy - sumX * sumY) / denom
  const b = (sumY - a * sumX) / n
  return a * tX + b
}

/** 表观密度校正系数与是否需要校正（偏差 > 2%）。 */
function calcDensityCorrection(
  measuredDensity: number | null,
  calcDensity: number | null,
): { factor: number | null; needs: boolean } {
  if (measuredDensity === null || measuredDensity <= 0) return { factor: null, needs: false }
  if (calcDensity === null || calcDensity <= 0) return { factor: null, needs: false }
  const factor = pyRound(measuredDensity / calcDensity, 6)
  const needs = Math.abs(measuredDensity - calcDensity) / calcDensity > 0.02
  return { factor, needs }
}

/** 对配合比各组分按统一校正系数缩放（百分比列不缩放）。 */
function applyCorrection(mix: UhpcTrialMixRowRes, factor: number | null): UhpcTrialMixRowRes {
  if (factor === null || factor <= 0) return emptyMix()
  const keys: Array<keyof UhpcTrialMixRowRes> = [
    'cement', 'fly_ash', 'micro_bead', 'silica_fume',
    'sand', 'steel_fiber', 'water', 'admixture', 'binder', 'total',
  ]
  const res = emptyMix()
  for (const key of keys) {
    const value = mix[key]
    res[key] = value !== null && value !== undefined ? pyRound((value as number) * factor, 1) : 0.0
  }
  // 百分比不应该乘系数
  res.admixture_pct = mix.admixture_pct ?? 0.0
  return res
}

/** UHPC 试配统一计算入口，输入/输出与后端 calc_uhpc_trial 一致。 */
export function calcUhpcTrial(req: UhpcTrialReq): UhpcTrialRes {
  const {
    wb, sb, alpha, sf_mass: sfMass, total,
    cement_pct: cementPct, fly_ash_pct: flyAshPct,
    micro_bead_pct: microBeadPct, silica_fume_pct: silicaFumePct,
    design_strength: designStrength,
    adjusted_sb: adjustedSb, adjusted_alpha: adjustedAlpha,
    s_wb_0: sWb0, s_wb_plus: sWbPlus, s_wb_minus: sWbMinus,
    s_sf_plus: sSfPlus, s_sf_minus: sSfMinus,
    a_wb_plus: aWbPlus, a_wb_minus: aWbMinus,
    a_sf_plus: aSfPlus, a_sf_minus: aSfMinus,
    corr_base: corrBase,
    measured_density: measuredDensity,
  } = req

  const trialSb = adjustedSb !== null ? adjustedSb : sb
  const trialAlpha = adjustedAlpha !== null ? adjustedAlpha : alpha

  // ── Tab 1: 试拌配合比 ──────────────────────────────────────────
  const trialMix = calcMix(
    wb, trialSb, trialAlpha, sfMass, total,
    cementPct, silicaFumePct, flyAshPct, microBeadPct,
  )

  // ── Tab 2: 强度变体 ────────────────────────────────────────────
  const variantWbPlus = calcMix(
    wb + 0.01, trialSb, trialAlpha, sfMass, total,
    cementPct, silicaFumePct, flyAshPct, microBeadPct, 0.0, aWbPlus,
  )
  const variantWbMinus = calcMix(
    wb - 0.01, trialSb, trialAlpha, sfMass, total,
    cementPct, silicaFumePct, flyAshPct, microBeadPct, 0.0, aWbMinus,
  )
  const variantSfPlus = calcMix(
    wb, trialSb, trialAlpha, sfMass, total,
    cementPct, silicaFumePct, flyAshPct, microBeadPct, 5.0, aSfPlus,
  )
  const variantSfMinus = calcMix(
    wb, trialSb, trialAlpha, sfMass, total,
    cementPct, silicaFumePct, flyAshPct, microBeadPct, -5.0, aSfMinus,
  )

  // 强度推荐 – 三点线性回归（配制强度在实测范围外时，选最接近的组）
  let recWb: number | null = null
  let recSf: number | null = null
  if (sWb0 !== null && sWbPlus !== null && sWbMinus !== null) {
    const wbXs = [wb + 0.01, wb, wb - 0.01]
    const wbYs = [sWbPlus, sWb0, sWbMinus]
    const minWy = Math.min(...wbYs)
    const maxWy = Math.max(...wbYs)
    if (designStrength > maxWy || designStrength < minWy) {
      // 配制强度在实测范围之外 → 选强度最接近的组对应的水胶比
      let closestIdx = 0
      let closestDist = Math.abs(wbYs[0] - designStrength)
      for (let i = 1; i < 3; i++) {
        const dist = Math.abs(wbYs[i] - designStrength)
        if (dist < closestDist) { closestDist = dist; closestIdx = i }
      }
      recWb = truncDigits(wbXs[closestIdx], 3)
    } else {
      recWb = truncDigits(
        linearFit(wb, sWb0, wb + 0.01, sWbPlus, wb - 0.01, sWbMinus, designStrength), 3,
      )
    }
  }
  if (sWb0 !== null && sSfPlus !== null && sSfMinus !== null) {
    const baseSf = trialMix.silica_fume
    const sfXs = [variantSfPlus.silica_fume, baseSf, variantSfMinus.silica_fume]
    const sfYs = [sSfPlus, sWb0, sSfMinus]
    const minSy = Math.min(...sfYs)
    const maxSy = Math.max(...sfYs)
    if (designStrength > maxSy || designStrength < minSy) {
      // 配制强度在实测范围之外 → 选强度最接近的组对应的硅灰用量
      let closestIdx = 0
      let closestDist = Math.abs(sfYs[0] - designStrength)
      for (let i = 1; i < 3; i++) {
        const dist = Math.abs(sfYs[i] - designStrength)
        if (dist < closestDist) { closestDist = dist; closestIdx = i }
      }
      recSf = truncDigits(sfXs[closestIdx], 1)
    } else {
      recSf = truncDigits(
        linearFit(
          baseSf, sWb0,
          variantSfPlus.silica_fume, sSfPlus,
          variantSfMinus.silica_fume, sSfMinus,
          designStrength,
        ),
        1,
      )
    }
  }

  // ── Tab 3: 校正配合比 ──────────────────────────────────────────
  let corrMix: UhpcTrialMixRowRes
  if (corrBase === 'wbRec' && recWb !== null) {
    const alphaBase = trialMix.binder > 0 ? (trialMix.admixture / trialMix.binder) * 100.0 : trialAlpha
    const alphaPlus = variantWbPlus.binder > 0 ? (variantWbPlus.admixture / variantWbPlus.binder) * 100.0 : trialAlpha
    const alphaMinus = variantWbMinus.binder > 0 ? (variantWbMinus.admixture / variantWbMinus.binder) * 100.0 : trialAlpha
    let fittedAlpha = linearPredict(
      wb, alphaBase, wb + 0.01, alphaPlus, wb - 0.01, alphaMinus, recWb,
    )
    fittedAlpha = Math.max(0.0, fittedAlpha)
    corrMix = calcMix(
      recWb, trialSb, fittedAlpha, sfMass, total,
      cementPct, silicaFumePct, flyAshPct, microBeadPct,
    )
  } else if (corrBase === 'sfRec' && recSf !== null) {
    const binder = trialMix.binder
    if (binder > 0) {
      const newSfPct = (recSf / binder) * 100.0
      const origSfPct = silicaFumePct
      const adjustedCePct = cementPct - (newSfPct - origSfPct)

      const baseSf = trialMix.silica_fume
      const alphaBase = (trialMix.admixture / trialMix.binder) * 100.0
      const alphaPlus = variantSfPlus.binder > 0 ? (variantSfPlus.admixture / variantSfPlus.binder) * 100.0 : trialAlpha
      const alphaMinus = variantSfMinus.binder > 0 ? (variantSfMinus.admixture / variantSfMinus.binder) * 100.0 : trialAlpha

      let fittedAlpha = linearPredict(
        baseSf, alphaBase,
        variantSfPlus.silica_fume, alphaPlus,
        variantSfMinus.silica_fume, alphaMinus,
        recSf,
      )
      fittedAlpha = Math.max(0.0, fittedAlpha)

      corrMix = calcMix(
        wb, trialSb, fittedAlpha, sfMass, total,
        adjustedCePct, newSfPct, flyAshPct, microBeadPct,
      )
    } else {
      corrMix = emptyMix()
    }
  } else {
    corrMix = trialMix
  }

  // 密度校正
  const calcDensity = corrMix.total > 0 ? corrMix.total : null
  const { factor: corrFactor, needs: needsCorr } = calcDensityCorrection(measuredDensity, calcDensity)
  const labMix = needsCorr ? applyCorrection(corrMix, corrFactor) : corrMix

  return {
    design_strength: designStrength,
    trial_sb: trialSb,
    trial_alpha: trialAlpha,
    trial_mix: trialMix,
    variant_wb_plus: variantWbPlus,
    variant_wb_minus: variantWbMinus,
    variant_sf_plus: variantSfPlus,
    variant_sf_minus: variantSfMinus,
    rec_wb: recWb,
    rec_sf: recSf,
    corr_base: corrBase,
    corr_mix: corrMix,
    calc_density: calcDensity,
    corr_factor: corrFactor,
    needs_corr: needsCorr,
    lab_mix: labMix,
  }
}
