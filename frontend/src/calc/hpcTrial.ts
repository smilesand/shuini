/**
 * calc/hpcTrial.ts
 * ================
 * 高性能（HPC）试配统一计算引擎，由后端 services/hpc_trial.py 迁移而来。
 *
 * 覆盖三步派生计算并保持原有顺序：
 *   1. 工作性实验 _calculateWorkabilityResult
 *   2. 试拌量换算  _calculateTrialMaterials
 *   3. 强度实验三组配合比 _calculateStrengthMixes
 *   4. 强度线性回归与推荐水胶比 _calculateStrengthRegression
 *   5. 强度关系图坐标 _calculateChartData
 *   6. 配合比校正「调整配合比」_calculateAdaptResult
 *   7. 表观密度校正系数 / 实验室配合比 _calculateLabMix
 *
 * 舍入口径：后端使用 `_round_js`（floor(x·f+0.5)/f）与 `_truncate_digits`，
 * 前端用 jsRound / truncDigits 一一对齐，保证跨端结果一致。
 */
import { jsRound, truncDigits } from './rounding'
import type {
  HpcTrialReq,
  HpcTrialRes,
  HpcTrialMaterialRowRes,
  HpcTrialMaterialResultRes,
  HpcTrialWorkabilityResultRes,
  HpcTrialStrengthMixRes,
  HpcTrialStrengthRegressionRes,
  HpcTrialChartDataRes,
} from '../api/calc'

const RECOMMEND_STRENGTH_MARGIN = 0.1
const RECOMMEND_WB_DIGITS = 2

/** 统一维护试配页展示的材料顺序。 */
const TRIAL_MATERIALS: ReadonlyArray<readonly [string, string]> = [
  ['mc', '水泥'],
  ['m1', '粉煤灰'],
  ['m2', '矿粉'],
  ['m3', '微珠'],
  ['m4', '硅灰'],
  ['mg', '粗骨料'],
  ['ms', '细骨料'],
  ['mw', '水'],
  ['ma', '外加剂'],
]

/** 复刻 Python `f"{value:g}"` 的紧凑数字格式，用于强度实验标签。 */
function formatDelta(value: number): string {
  // Python :g 默认 6 位有效数字，去除多余尾零；JS toString 在这些小数上等价。
  return Number.parseFloat(value.toPrecision(6)).toString()
}

function emptyWorkabilityResult(): HpcTrialWorkabilityResultRes {
  return {
    mc: null, m1: null, m2: null, m3: null, m4: null,
    mg: null, ms: null, mw: null, ma: null,
    mb: null, wb: null, bs: null, alpha: null, total: null,
  }
}

function emptyStrengthMix(label = ''): HpcTrialStrengthMixRes {
  return {
    label, wb: null, bs: null,
    mc: null, m1: null, m2: null, m3: null, m4: null,
    mg: null, ms: null, mw: null, ma: null, mb: null, total: null,
  }
}

function emptyMaterialResult(): HpcTrialMaterialResultRes {
  return {
    mc: null, m1: null, m2: null, m3: null, m4: null,
    mg: null, ms: null, mw: null, ma: null, total: null,
  }
}

function emptyTrialMaterials(): HpcTrialMaterialRowRes[] {
  return TRIAL_MATERIALS.map(([key, label]) => ({ key, label, trial_val: null }))
}

/** 按「胶材总量 mb」计算各胶材组分质量分数（分母为设计胶材总量）。 */
function componentFractionsFromBinderTotal(
  binderTotal: number,
  cement: number,
  flyAsh: number,
  slag: number,
  microBead: number,
  silicaFume: number,
): Record<string, number> | null {
  if (binderTotal <= 0 || cement < 0) return null
  return {
    mc: cement / binderTotal,
    m1: flyAsh / binderTotal,
    m2: slag / binderTotal,
    m3: microBead / binderTotal,
    m4: silicaFume / binderTotal,
  }
}

/** 工作性实验：水胶比不变，调整胶材总量/砂率/外加剂掺量重算每方用量。 */
function calculateWorkabilityResult(
  wb: number, betaS: number, mb: number,
  mc: number, m1: number, m2: number, m3: number, m4: number,
  mg: number, ms: number, alpha: number,
  workabilityBinderDelta: number,
  workabilitySandRatioDelta: number,
  workabilityAlphaDelta: number,
): HpcTrialWorkabilityResultRes {
  const fractions = componentFractionsFromBinderTotal(mb, mc, m1, m2, m3, m4)
  const totalAggregate = mg + ms
  if (
    fractions === null || wb <= 0 || betaS <= 0 || betaS >= 100 ||
    totalAggregate <= 0 || alpha < 0
  ) {
    return emptyWorkabilityResult()
  }

  const adjustedBinder = mb + workabilityBinderDelta
  const adjustedSandRatio = betaS + workabilitySandRatioDelta
  const adjustedAlpha = alpha + workabilityAlphaDelta

  if (
    adjustedBinder <= 0 || adjustedSandRatio <= 0 ||
    adjustedSandRatio >= 100 || adjustedAlpha < 0
  ) {
    return emptyWorkabilityResult()
  }

  const adjustedWater = adjustedBinder * wb
  const adjustedAdmixture = adjustedBinder * (adjustedAlpha / 100.0)
  const adjustedSand = totalAggregate * (adjustedSandRatio / 100.0)
  const adjustedCoarse = totalAggregate - adjustedSand

  const cement = adjustedBinder * fractions.mc
  const flyAsh = adjustedBinder * fractions.m1
  const slag = adjustedBinder * fractions.m2
  const microBead = adjustedBinder * fractions.m3
  const silicaFume = adjustedBinder * fractions.m4
  const total =
    cement + flyAsh + slag + microBead + silicaFume +
    adjustedCoarse + adjustedSand + adjustedWater + adjustedAdmixture

  return {
    mc: jsRound(cement, 2),
    m1: jsRound(flyAsh, 2),
    m2: jsRound(slag, 2),
    m3: jsRound(microBead, 2),
    m4: jsRound(silicaFume, 2),
    mg: jsRound(adjustedCoarse, 2),
    ms: jsRound(adjustedSand, 2),
    mw: jsRound(adjustedWater, 2),
    ma: jsRound(adjustedAdmixture, 2),
    mb: jsRound(adjustedBinder, 2),
    wb: jsRound(adjustedWater / adjustedBinder, 4),
    bs: jsRound(adjustedSandRatio, 2),
    alpha: jsRound(adjustedAlpha, 2),
    total: jsRound(total, 2),
  }
}

/** 试拌量换算：按试拌体积将每方结果换算为批量用量。 */
function calculateTrialMaterials(
  workabilityResult: HpcTrialWorkabilityResultRes,
  batchVolume: number,
): HpcTrialMaterialRowRes[] {
  if (batchVolume <= 0) return emptyTrialMaterials()
  const factor = batchVolume / 1000.0
  return TRIAL_MATERIALS.map(([key, label]) => {
    const value = (workabilityResult as unknown as Record<string, number | null>)[key]
    return {
      key,
      label,
      trial_val: value === null || value === undefined ? null : jsRound(value * factor, 3),
    }
  })
}

/** 强度实验三组配合比：以工作性结果为优先基准，回退到设计配合比。 */
function calculateStrengthMixes(
  wb: number, betaS: number, mb: number,
  mc: number, m1: number, m2: number, m3: number, m4: number,
  mg: number, ms: number, mw: number, alpha: number,
  workabilityResult: HpcTrialWorkabilityResultRes,
  deltaWb: number, deltaBs: number,
  trialAlpha?: number | null,
  trialMa0?: number | null,
  trialMaP?: number | null,
  trialMaN?: number | null,
): HpcTrialStrengthMixRes[] {
  const pick = (v: number | null | undefined, fallback: number): number =>
    v === null || v === undefined ? fallback : v

  const binder = pick(workabilityResult.mb, mb)
  const cement = pick(workabilityResult.mc, mc)
  const flyAsh = pick(workabilityResult.m1, m1)
  const slag = pick(workabilityResult.m2, m2)
  const microBead = pick(workabilityResult.m3, m3)
  const silicaFume = pick(workabilityResult.m4, m4)
  const coarse = pick(workabilityResult.mg, mg)
  const fine = pick(workabilityResult.ms, ms)
  // water 在后端未直接使用，但保留以对齐分支逻辑
  void mw
  const resolvedWb = pick(workabilityResult.wb, wb)
  const resolvedBs = pick(workabilityResult.bs, betaS)
  const resolvedAlpha = pick(workabilityResult.alpha, alpha)

  const strengthAlpha = trialAlpha !== null && trialAlpha !== undefined ? trialAlpha : resolvedAlpha

  if (
    binder <= 0 || resolvedWb <= 0 ||
    Number.isNaN(binder) || Number.isNaN(resolvedWb) || Number.isNaN(strengthAlpha)
  ) {
    return []
  }

  const totalAggregate = coarse + fine
  const variants = [
    { label: '基准', wb: resolvedWb, bs: resolvedBs },
    {
      label: `W/B+${deltaWb.toFixed(2)} βs+${formatDelta(deltaBs)}%`,
      wb: resolvedWb + deltaWb,
      bs: resolvedBs + deltaBs,
    },
    {
      label: `W/B-${deltaWb.toFixed(2)} βs-${formatDelta(deltaBs)}%`,
      wb: resolvedWb - deltaWb,
      bs: resolvedBs - deltaBs,
    },
  ]

  const maOverrides: Array<number | null | undefined> = [trialMa0, trialMaP, trialMaN]
  const mixes: HpcTrialStrengthMixRes[] = []

  variants.forEach((variant, idx) => {
    if (variant.wb <= 0 || variant.bs <= 0 || variant.bs >= 100) {
      mixes.push(emptyStrengthMix(variant.label))
      return
    }
    const adjustedWater = binder * variant.wb
    if (adjustedWater <= 0) {
      mixes.push(emptyStrengthMix(variant.label))
      return
    }
    const adjustedSand = totalAggregate * (variant.bs / 100.0)
    const adjustedCoarse = totalAggregate - adjustedSand

    const override = maOverrides[idx]
    const adjustedAdmixture =
      override !== null && override !== undefined ? override : binder * (strengthAlpha / 100.0)

    const total =
      cement + flyAsh + slag + microBead + silicaFume +
      adjustedCoarse + adjustedSand + adjustedWater + adjustedAdmixture

    mixes.push({
      label: variant.label,
      wb: jsRound(variant.wb, 2),
      bs: jsRound(variant.bs, 2),
      mc: jsRound(cement, 2),
      m1: jsRound(flyAsh, 2),
      m2: jsRound(slag, 2),
      m3: jsRound(microBead, 2),
      m4: jsRound(silicaFume, 2),
      mg: jsRound(adjustedCoarse, 2),
      ms: jsRound(adjustedSand, 2),
      mw: jsRound(adjustedWater, 2),
      ma: jsRound(adjustedAdmixture, 2),
      mb: jsRound(binder, 2),
      total: jsRound(total, 2),
    })
  })

  return mixes
}

/** 强度线性回归（Bolomey 公式形式）：f_cu = a × (C/W) + b。
 *  由目标强度反推推荐胶水比 C/W_rec，再线性插值得推荐砂率。
 *  若推荐 C/W 恰等于某对照组 C/W（容差 1e-6），直接取该组的 wb/bs 精确值。 */
function calculateStrengthRegression(
  strengthMixes: HpcTrialStrengthMixRes[],
  strength0: number | null,
  strengthP: number | null,
  strengthN: number | null,
  targetStrength: number | null,
): HpcTrialStrengthRegressionRes | null {
  const strengths = [strength0, strengthP, strengthN]
  if (strengthMixes.length < 3 || strengths.some((v) => v === null)) return null

  // 提取三组 C/W 和 bs
  const cwVals: number[] = []
  const bsVals: number[] = []
  for (let i = 0; i < 3; i++) {
    const wb = strengthMixes[i].wb
    const bs = strengthMixes[i].bs
    if (wb === null || wb <= 0 || bs === null) return null
    cwVals.push(1.0 / wb)
    bsVals.push(bs)
  }

  // Bolomey 线性回归: f_cu = a·(C/W) + b
  const sVals = strengths as number[]
  const n = 3
  const sumX = cwVals.reduce((s, v) => s + v, 0)
  const sumY = sVals.reduce((s, v) => s + v, 0)
  const sumXY = cwVals.reduce((s, cw, i) => s + cw * sVals[i], 0)
  const sumX2 = cwVals.reduce((s, cw) => s + cw * cw, 0)
  const denom = n * sumX2 - sumX * sumX
  if (Math.abs(denom) < 1e-9) return null

  const a = (n * sumXY - sumX * sumY) / denom
  const b = (sumY - a * sumX) / n
  const avgY = sumY / n
  const ssTot = sVals.reduce((s, v) => s + (v - avgY) ** 2, 0)
  const ssRes = sVals.reduce((s, v, i) => s + (v - (a * cwVals[i] + b)) ** 2, 0)
  const r2 = ssTot === 0 ? 1.0 : 1.0 - ssRes / ssTot

  let recommendWb: number | null = null
  let recommendBs: number | null = null
  let predictStrength: number | null = null
  let matchGroupIndex = -1

  if (targetStrength !== null && Math.abs(a) > 1e-9) {
    const recommendedStrength = targetStrength + RECOMMEND_STRENGTH_MARGIN
    // Bolomey: C/W_rec = (target - b) / a
    const cwRec = (recommendedStrength - b) / a
    if (cwRec > 0) {
      recommendWb = jsRound(1.0 / cwRec, 2)

      // 用 W/B 保留两位小数后的值匹配对照组（而非浮点 C/W），
      // 消除回归系数浮点误差导致的匹配失败。容差 0.005 覆盖 2dp 舍入边界。
      const wbRounded = recommendWb
      const matchIdx = strengthMixes.findIndex(
        (mix) => mix.wb !== null && Math.abs(mix.wb - wbRounded) < 0.005,
      )
      if (matchIdx >= 0) {
        // 精确匹配：取对照组 wb/bs 并标记
        recommendBs = jsRound(strengthMixes[matchIdx].bs!, 2)
        matchGroupIndex = matchIdx
      } else {
        // 无匹配：线性插值砂率 bs = c·(C/W) + d
        const sumBs = bsVals.reduce((s, v) => s + v, 0)
        const sumCwBs = cwVals.reduce((s, cw, i) => s + cw * bsVals[i], 0)
        const denomBs = n * sumX2 - sumX * sumX
        if (Math.abs(denomBs) > 1e-9) {
          const c_coef = (n * sumCwBs - sumX * sumBs) / denomBs
          const d_coef = (sumBs - c_coef * sumX) / n
          recommendBs = jsRound(c_coef * cwRec + d_coef, 2)
        }
      }

      predictStrength = jsRound(a * cwRec + b, 1)
    }
  }

  return {
    a: jsRound(a, 4),
    b: jsRound(b, 2),
    r2: jsRound(r2, 4),
    recommend_wb: recommendWb,
    recommend_bs: recommendBs,
    match_group_index: matchGroupIndex,
    predict_strength: predictStrength,
  }
}

/** 强度关系图坐标范围与散点数据。 */
function calculateChartData(
  strengthMixes: HpcTrialStrengthMixRes[],
  strength0: number | null,
  strengthP: number | null,
  strengthN: number | null,
): HpcTrialChartDataRes | null {
  const strengths = [strength0, strengthP, strengthN]
  if (strengthMixes.length < 3 || strengths.some((v) => v === null)) return null

  const bwRatios: number[] = []
  for (let i = 0; i < 3; i++) {
    const mixWb = strengthMixes[i].wb
    if (mixWb === null || mixWb <= 0) return null
    bwRatios.push(jsRound(1.0 / mixWb, 4))
  }

  const strengthValues = strengths.filter((v) => v !== null) as number[]
  const rawMinBw = Math.min(...bwRatios)
  const rawMaxBw = Math.max(...bwRatios)
  const rawMinStrength = Math.min(...strengthValues)
  const rawMaxStrength = Math.max(...strengthValues)
  const minBw = jsRound(rawMinBw - 0.05, 4)
  const maxBw = jsRound(rawMaxBw + 0.05, 4)
  const minStrength = Math.floor(rawMinStrength - 2)
  const maxStrength = Math.ceil(rawMaxStrength + 2)

  return {
    min_bw: minBw,
    max_bw: maxBw,
    range_bw: Math.max(maxBw - minBw, 0.0001),
    min_strength: minStrength,
    max_strength: maxStrength,
    range_strength: Math.max(maxStrength - minStrength, 0.1),
    bw_ratios: bwRatios,
    strengths: strengthValues,
  }
}

/** 配合比校正「调整配合比」：以设计胶材总量算分项比例，粗骨料不变。 */
function calculateAdaptResult(
  wb: number, betaS: number, mb: number,
  mc: number, m1: number, m2: number, m3: number, m4: number,
  mg: number, alpha: number,
  wbAdj: number | null, mbAdj: number | null,
  sandRatioAdj: number | null, alphaAdj: number | null,
): HpcTrialMaterialResultRes {
  const fractions = componentFractionsFromBinderTotal(mb, mc, m1, m2, m3, m4)
  if (fractions === null || mg <= 0) return emptyMaterialResult()

  const resolvedWb = wbAdj === null ? wb : wbAdj
  const resolvedMb = mbAdj === null ? mb : mbAdj
  const resolvedBs = sandRatioAdj === null ? betaS : sandRatioAdj
  const resolvedAlpha = alphaAdj === null ? alpha : alphaAdj

  if (
    resolvedWb <= 0 || resolvedMb <= 0 ||
    resolvedBs <= 0 || resolvedBs >= 100 || resolvedAlpha < 0
  ) {
    return emptyMaterialResult()
  }

  const sandRatioDecimal = resolvedBs / 100.0
  const cementMass = resolvedMb * fractions.mc
  const flyAsh = resolvedMb * fractions.m1
  const slag = resolvedMb * fractions.m2
  const microBead = resolvedMb * fractions.m3
  const silicaFume = resolvedMb * fractions.m4
  const sand = (sandRatioDecimal / (1.0 - sandRatioDecimal)) * mg
  const water = resolvedMb * resolvedWb
  const admixture = resolvedMb * (resolvedAlpha / 100.0)
  const total =
    cementMass + flyAsh + slag + microBead + silicaFume + mg + sand + water + admixture

  return {
    mc: jsRound(cementMass, 2),
    m1: jsRound(flyAsh, 2),
    m2: jsRound(slag, 2),
    m3: jsRound(microBead, 2),
    m4: jsRound(silicaFume, 2),
    mg: jsRound(mg, 2),
    ms: jsRound(sand, 2),
    mw: jsRound(water, 2),
    ma: jsRound(admixture, 2),
    total: jsRound(total, 2),
  }
}

/** 表观密度校正系数 = 实测 / 计算。 */
function calculateDensityCorrectionFactor(
  measuredDensity: number | null,
  calculatedDensity: number | null,
): number | null {
  if (
    measuredDensity === null || measuredDensity <= 0 ||
    calculatedDensity === null || calculatedDensity <= 0
  ) {
    return null
  }
  return jsRound(measuredDensity / calculatedDensity, 6)
}

/** 实验室配合比：按密度校正系数统一缩放调整配合比。 */
function calculateLabMix(
  adaptResult: HpcTrialMaterialResultRes,
  densityCorrectionFactor: number | null,
): HpcTrialMaterialResultRes {
  if (densityCorrectionFactor === null || densityCorrectionFactor <= 0) {
    return emptyMaterialResult()
  }
  const scale = (v: number | null): number | null =>
    v === null ? null : jsRound(v * densityCorrectionFactor, 2)
  return {
    mc: scale(adaptResult.mc),
    m1: scale(adaptResult.m1),
    m2: scale(adaptResult.m2),
    m3: scale(adaptResult.m3),
    m4: scale(adaptResult.m4),
    mg: scale(adaptResult.mg),
    ms: scale(adaptResult.ms),
    mw: scale(adaptResult.mw),
    ma: scale(adaptResult.ma),
    total: scale(adaptResult.total),
  }
}

/** HPC 试配统一计算入口，输入/输出与后端 calc_hpc_trial 完全一致。 */
export function calcHpcTrial(req: HpcTrialReq): HpcTrialRes {
  const workabilityResult = calculateWorkabilityResult(
    req.wb, req.beta_s, req.mb,
    req.mc, req.m1, req.m2, req.m3, req.m4,
    req.mg, req.ms, req.alpha,
    req.workability_binder_delta,
    req.workability_sand_ratio_delta,
    req.workability_alpha_delta,
  )
  const trialMaterials = calculateTrialMaterials(workabilityResult, req.batch_volume)
  const baseWb = workabilityResult.wb !== null ? workabilityResult.wb : req.wb
  const baseBs = workabilityResult.bs !== null ? workabilityResult.bs : req.beta_s
  const baseAlpha = workabilityResult.alpha !== null ? workabilityResult.alpha : req.alpha

  const strengthMixes = calculateStrengthMixes(
    req.wb, req.beta_s, req.mb,
    req.mc, req.m1, req.m2, req.m3, req.m4,
    req.mg, req.ms, req.mw, req.alpha,
    workabilityResult,
    req.delta_wb, req.delta_bs,
    req.trial_alpha, req.trial_ma0, req.trial_maP, req.trial_maN,
  )
  const strengthRegression = calculateStrengthRegression(
    strengthMixes, req.strength0, req.strength_p, req.strength_n, req.target_strength,
  )
  const chartData = calculateChartData(strengthMixes, req.strength0, req.strength_p, req.strength_n)

  const adaptResult = calculateAdaptResult(
    req.wb, req.beta_s, req.mb,
    req.mc, req.m1, req.m2, req.m3, req.m4,
    req.mg, req.alpha,
    req.wb_adj, req.mb_adj, req.sand_ratio_adj, req.alpha_adj,
  )

  // 当推荐值与对照组匹配时，调整配合比应直接取对照组数据确保一致
  if (strengthRegression && strengthRegression.match_group_index >= 0) {
    const matchedMix = strengthMixes[strengthRegression.match_group_index]
    if (matchedMix && matchedMix.mc !== null) {
      adaptResult.mc = matchedMix.mc
      adaptResult.m1 = matchedMix.m1
      adaptResult.m2 = matchedMix.m2
      adaptResult.m3 = matchedMix.m3
      adaptResult.m4 = matchedMix.m4
      adaptResult.mg = matchedMix.mg
      adaptResult.ms = matchedMix.ms
      adaptResult.mw = matchedMix.mw
      adaptResult.ma = matchedMix.ma
      adaptResult.total = matchedMix.total
    }
  }

  const calculatedDensity = adaptResult.total
  const densityCorrectionFactor = calculateDensityCorrectionFactor(req.measured_density, calculatedDensity)
  const labMix = calculateLabMix(adaptResult, densityCorrectionFactor)

  return {
    base_wb: baseWb,
    base_bs: baseBs,
    base_alpha: baseAlpha,
    workability_result: workabilityResult,
    trial_materials: trialMaterials,
    strength_mixes: strengthMixes,
    strength_regression: strengthRegression,
    chart_data: chartData,
    adapt_result: adaptResult,
    calculated_density: calculatedDensity,
    density_correction_factor: densityCorrectionFactor,
    lab_mix: labMix,
  }
}
