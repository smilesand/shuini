import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { calcHpcTrial, type HpcTrialReq, type HpcTrialRes } from '../api/calc'
import { useCalcStore } from '../stores/calcStore'
import { evaluateHpcWorkability, getHpcWorkabilityReference } from '../utils/hpcWorkability'
import { type StrengthGroup, computeGroupValue } from './useStrengthEval'

export type HpcTrialTab = 'workability' | 'strength' | 'correction'

type NullableNumber = number | null

export interface TrialMatCol {
  key: string
  label: string
  trialVal: NullableNumber
}

export interface WorkabilityAdjResult {
  mc: NullableNumber
  m1: NullableNumber
  m2: NullableNumber
  m3: NullableNumber
  m4: NullableNumber
  mg: NullableNumber
  ms: NullableNumber
  mw: NullableNumber
  ma: NullableNumber
  mb: NullableNumber
  wb: NullableNumber
  bs: NullableNumber
  alpha: NullableNumber
  total: NullableNumber
}

export interface StrengthMix {
  label: string
  wb: NullableNumber
  bs: NullableNumber
  mc: NullableNumber
  m1: NullableNumber
  m2: NullableNumber
  m3: NullableNumber
  m4: NullableNumber
  mg: NullableNumber
  ms: NullableNumber
  mw: NullableNumber
  ma: NullableNumber
  mb: NullableNumber
  total: NullableNumber
}

export interface StrengthRegression {
  a: number
  b: number
  r2: number
  recommendWb: NullableNumber
  predictStrength: NullableNumber
}

export interface ChartData {
  minBW: number
  maxBW: number
  rangeBW: number
  minStrength: number
  maxStrength: number
  rangeStrength: number
  bwRatios: number[]
  strengths: number[]
}

export interface AdaptResult {
  mc: NullableNumber
  m1: NullableNumber
  m2: NullableNumber
  m3: NullableNumber
  m4: NullableNumber
  mg: NullableNumber
  ms: NullableNumber
  mw: NullableNumber
  ma: NullableNumber
  total: NullableNumber
}

export interface LabMixRow {
  mc: NullableNumber
  m1: NullableNumber
  m2: NullableNumber
  m3: NullableNumber
  m4: NullableNumber
  mg: NullableNumber
  ms: NullableNumber
  mw: NullableNumber
  ma: NullableNumber
  total: NullableNumber
}

interface TrialCalculatedState {
  baseWb: NullableNumber
  baseBs: NullableNumber
  baseAlpha: NullableNumber
  workabilityResult: WorkabilityAdjResult
  trialMatCols: TrialMatCol[]
  strengthMixes: StrengthMix[]
  strengthRegression: StrengthRegression | null
  chartData: ChartData | null
  adaptResult: AdaptResult
  calculatedDensity: NullableNumber
  densityCorrectionFactor: NullableNumber
  labMix: LabMixRow
}

interface TrialInputSnapshot {
  batchVolume: number
  workabilityBinderDelta: number
  workabilitySandRatioDelta: number
  workabilityAlphaDelta: number
  slumpMeasured: NullableNumber
  spreadMeasured: NullableNumber
  workabilityOk: boolean
  workabilityNote: string
  deltaWb: number
  deltaBs: number
  strength0: NullableNumber
  strengthP: NullableNumber
  strengthN: NullableNumber
  sTargetStrength: NullableNumber
  wbAdj: NullableNumber
  mbAdj: NullableNumber
  sandRatioAdj: NullableNumber
  alphaAdj: NullableNumber
  measuredDensity: NullableNumber
  evalStrength28d: NullableNumber
  evalSlump: NullableNumber
  evalSpread: NullableNumber
  evalWorkabilityDesc: string
}

export interface TrialSnapshot {
  version: number
  inputs: TrialInputSnapshot
  calculated: TrialCalculatedState
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function toNullableNumber(value: unknown): NullableNumber {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function toNumber(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function toStringValue(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function normalizeRecommendedWb(value: NullableNumber): NullableNumber {
  if (value === null || !Number.isFinite(value)) {
    return null
  }

  return Math.floor(value * 100) / 100
}

function resolveDefaultStrength(value: NullableNumber): NullableNumber {
  return value !== null && Number.isFinite(value) ? value : null
}

function emptyWorkabilityResult(): WorkabilityAdjResult {
  return {
    mc: null,
    m1: null,
    m2: null,
    m3: null,
    m4: null,
    mg: null,
    ms: null,
    mw: null,
    ma: null,
    mb: null,
    wb: null,
    bs: null,
    alpha: null,
    total: null,
  }
}

function emptyStrengthMix(label = ''): StrengthMix {
  return {
    label,
    wb: null,
    bs: null,
    mc: null,
    m1: null,
    m2: null,
    m3: null,
    m4: null,
    mg: null,
    ms: null,
    mw: null,
    ma: null,
    mb: null,
    total: null,
  }
}

function emptyAdaptResult(): AdaptResult {
  return {
    mc: null,
    m1: null,
    m2: null,
    m3: null,
    m4: null,
    mg: null,
    ms: null,
    mw: null,
    ma: null,
    total: null,
  }
}

function emptyLabMix(): LabMixRow {
  return {
    mc: null,
    m1: null,
    m2: null,
    m3: null,
    m4: null,
    mg: null,
    ms: null,
    mw: null,
    ma: null,
    total: null,
  }
}

function defaultStrengthGroups(): StrengthGroup[] {
  let n = 1
  return Array.from({ length: 6 }, () => ({
    id: `G${String(n++).padStart(2, '0')}`,
    values: [null, null, null] as (number | null)[],
  }))
}

function emptyTrialMatCols(): TrialMatCol[] {
  return [
    { key: 'mc', label: '水泥', trialVal: null },
    { key: 'm1', label: '粉煤灰', trialVal: null },
    { key: 'm2', label: '矿粉', trialVal: null },
    { key: 'm3', label: '微珠', trialVal: null },
    { key: 'm4', label: '硅灰', trialVal: null },
    { key: 'mg', label: '粗骨料', trialVal: null },
    { key: 'ms', label: '细骨料', trialVal: null },
    { key: 'mw', label: '水', trialVal: null },
    { key: 'ma', label: '外加剂', trialVal: null },
  ]
}

function emptyCalculatedState(): TrialCalculatedState {
  return {
    baseWb: null,
    baseBs: null,
    baseAlpha: null,
    workabilityResult: emptyWorkabilityResult(),
    trialMatCols: emptyTrialMatCols(),
    strengthMixes: [],
    strengthRegression: null,
    chartData: null,
    adaptResult: emptyAdaptResult(),
    calculatedDensity: null,
    densityCorrectionFactor: null,
    labMix: emptyLabMix(),
  }
}

function mapMaterialResult(result: HpcTrialRes['adapt_result']): AdaptResult {
  return {
    mc: result.mc,
    m1: result.m1,
    m2: result.m2,
    m3: result.m3,
    m4: result.m4,
    mg: result.mg,
    ms: result.ms,
    mw: result.mw,
    ma: result.ma,
    total: result.total,
  }
}

function mapWorkabilityResult(result: HpcTrialRes['workability_result']): WorkabilityAdjResult {
  return {
    mc: result.mc,
    m1: result.m1,
    m2: result.m2,
    m3: result.m3,
    m4: result.m4,
    mg: result.mg,
    ms: result.ms,
    mw: result.mw,
    ma: result.ma,
    mb: result.mb,
    wb: result.wb,
    bs: result.bs,
    alpha: result.alpha,
    total: result.total,
  }
}

function mapStrengthMix(mix: HpcTrialRes['strength_mixes'][number]): StrengthMix {
  return {
    label: mix.label,
    wb: mix.wb,
    bs: mix.bs,
    mc: mix.mc,
    m1: mix.m1,
    m2: mix.m2,
    m3: mix.m3,
    m4: mix.m4,
    mg: mix.mg,
    ms: mix.ms,
    mw: mix.mw,
    ma: mix.ma,
    mb: mix.mb,
    total: mix.total,
  }
}

function mapTrialResponse(response: HpcTrialRes): TrialCalculatedState {
  return {
    baseWb: response.base_wb,
    baseBs: response.base_bs,
    baseAlpha: response.base_alpha,
    workabilityResult: mapWorkabilityResult(response.workability_result),
    trialMatCols: response.trial_materials.map((item) => ({
      key: item.key,
      label: item.label,
      trialVal: item.trial_val,
    })),
    strengthMixes: response.strength_mixes.map(mapStrengthMix),
    strengthRegression: response.strength_regression ? {
      a: response.strength_regression.a,
      b: response.strength_regression.b,
      r2: response.strength_regression.r2,
      recommendWb: normalizeRecommendedWb(response.strength_regression.recommend_wb),
      predictStrength: response.strength_regression.predict_strength,
    } : null,
    chartData: response.chart_data ? {
      minBW: response.chart_data.min_bw,
      maxBW: response.chart_data.max_bw,
      rangeBW: response.chart_data.range_bw,
      minStrength: response.chart_data.min_strength,
      maxStrength: response.chart_data.max_strength,
      rangeStrength: response.chart_data.range_strength,
      bwRatios: response.chart_data.bw_ratios,
      strengths: response.chart_data.strengths,
    } : null,
    adaptResult: mapMaterialResult(response.adapt_result),
    calculatedDensity: response.calculated_density,
    densityCorrectionFactor: response.density_correction_factor,
    labMix: mapMaterialResult(response.lab_mix),
  }
}

export function useHpcTrial() {
  const store = useCalcStore()

  const wbAdj = ref<NullableNumber>(null)
  const mbAdj = ref<NullableNumber>(null)
  const sandRatioAdj = ref<NullableNumber>(null)
  const alphaAdj = ref<NullableNumber>(null)

  const batchVolume = ref(20)
  const workabilityBinderDelta = ref(0)
  const workabilitySandRatioDelta = ref(0)
  const workabilityAlphaDelta = ref(0)
  const slumpMeasured = ref<NullableNumber>(null)
  const spreadMeasured = ref<NullableNumber>(null)
  const workabilityNote = ref('')

  const deltaWb = ref(0.02)
  const deltaBs = ref(2)
  const strength0 = ref<NullableNumber>(null)
  const strengthP = ref<NullableNumber>(null)
  const strengthN = ref<NullableNumber>(null)
  const sTargetStrength = ref<NullableNumber>(null)
  const strengthAlpha = ref<NullableNumber>(null)
  // Per-group admixture overrides (null = use computed from trial_alpha)
  const strengthMa0 = ref<NullableNumber>(null)
  const strengthMaP = ref<NullableNumber>(null)
  const strengthMaN = ref<NullableNumber>(null)

  const measuredDensity = ref<NullableNumber>(null)
  const strengthGroups = ref<StrengthGroup[]>(defaultStrengthGroups())
  const evalSlump = ref<NullableNumber>(null)
  const evalSpread = ref<NullableNumber>(null)
  const evalWorkabilityDesc = ref<string>('')
  const loading = ref(false)
  const error = ref<string | null>(null)
  const calculated = ref<TrialCalculatedState>(emptyCalculatedState())
  const hasSavedTrialData = computed(() => isPlainObject(store.currentTrialData))

  const wbVal = computed(() => store.wb)
  const sandRatioVal = computed(() => store.sandRatioConfirmed ? store.sandRatioInput : null)
  const mbVal = computed(() => store.mb)
  const mcVal = computed(() => store.mc)
  const m1Val = computed(() => store.b1p && store.b1p > 0 ? store.m1 : null)
  const m2Val = computed(() => store.b2p && store.b2p > 0 ? store.m2 : null)
  const m3Val = computed(() => store.b3p && store.b3p > 0 ? store.m3 : null)
  const m4Val = computed(() => store.b4p && store.b4p > 0 ? store.m4 : null)
  const mgVal = computed(() => store.mg)
  const msVal = computed(() => store.ms)
  const mwVal = computed(() => store.mw)
  const maVal = computed(() => store.ma)
  const alphaVal = computed(() => store.alpha)
  const selectedWorkabilityReference = computed(() => getHpcWorkabilityReference(store.vgReferenceCode))
  const workabilityEvaluation = computed(() => evaluateHpcWorkability(
    store.vgReferenceCode,
    slumpMeasured.value,
    spreadMeasured.value,
  ))
  const workabilityOk = computed(() => workabilityEvaluation.value.status === 'pass')

  // ── Group-based 28d strength evaluation ────────────────────
  const groupResults = computed(() =>
    strengthGroups.value.map(g => computeGroupValue(g.values)),
  )

  const strengthOverallAvg = computed<number | null>(() => {
    const vals = groupResults.value.map(r => r.value).filter((v): v is number => v !== null)
    if (vals.length === 0) return null
    return vals.reduce((s, v) => s + v, 0) / vals.length
  })

  const strengthMinGroupAvg = computed<number | null>(() => {
    const vals = groupResults.value.map(r => r.value).filter((v): v is number => v !== null)
    if (vals.length === 0) return null
    return Math.min(...vals)
  })

  const allGroupsComplete = computed(() =>
    groupResults.value.length >= 6 && groupResults.value.every(r => r.value !== null),
  )

  const strengthEvaluation = computed(() => {
    const target = sTargetStrength.value
    const ov = strengthOverallAvg.value
    const minG = strengthMinGroupAvg.value
    const sg = store.fcuk !== null && Number.isFinite(store.fcuk) ? store.fcuk : null

    if (target === null) {
      return {
        status: 'pending' as const,
        label: '待评价',
        tagType: 'info' as const,
        detail: '请先在主计算页完成配制强度计算。',
      }
    }

    if (!allGroupsComplete.value || ov === null) {
      return {
        status: 'pending' as const,
        label: '待输入',
        tagType: 'info' as const,
        detail: '请完成所有 6 组（每组 3 条）28d 抗压强度数据填写。',
      }
    }

    const overallPass = ov >= target
    const minThreshold = sg !== null && Number.isFinite(sg) ? sg * 0.95 : null
    const minGroupPass = minThreshold !== null && minG !== null ? minG >= minThreshold : null
    const allPass = overallPass && (minGroupPass !== false)

    let detail = `总体平均值 ${ov.toFixed(1)} MPa`
    detail += overallPass
      ? ` ≥ 配制强度 ${target.toFixed(1)} MPa`
      : ` < 配制强度 ${target.toFixed(1)} MPa，差值 ${(target - ov).toFixed(1)} MPa`

    if (minThreshold !== null && minG !== null) {
      detail += `；组均值最小值 ${minG.toFixed(1)} MPa`
      detail += minGroupPass
        ? ` ≥ 0.95×强度等级(${minThreshold.toFixed(1)} MPa)`
        : ` < 0.95×强度等级(${minThreshold.toFixed(1)} MPa)`
    }

    return {
      status: allPass ? ('pass' as const) : ('fail' as const),
      label: allPass ? '合格' : '不合格',
      tagType: allPass ? ('success' as const) : ('danger' as const),
      detail,
    }
  })

  const hasData = computed(() => (
    wbVal.value !== null
    && sandRatioVal.value !== null
    && mbVal.value !== null
    && mgVal.value !== null
    && msVal.value !== null
    && mwVal.value !== null
    && maVal.value !== null
  ))

  // 将所有会影响试配结果的输入集中暴露给视图层，
  // 由视图层用与主计算页一致的 debounce 方式触发后端重算。
  const calculationDeps = computed(() => ([
    store.currentRecordId,
    wbVal.value,
    sandRatioVal.value,
    mbVal.value,
    mcVal.value,
    m1Val.value,
    m2Val.value,
    m3Val.value,
    m4Val.value,
    mgVal.value,
    msVal.value,
    mwVal.value,
    alphaVal.value,
    batchVolume.value,
    workabilityBinderDelta.value,
    workabilitySandRatioDelta.value,
    workabilityAlphaDelta.value,
    deltaWb.value,
    deltaBs.value,
    strength0.value,
    strengthP.value,
    strengthN.value,
    sTargetStrength.value,
    strengthAlpha.value,
    strengthMa0.value,
    strengthMaP.value,
    strengthMaN.value,
    wbAdj.value,
    mbAdj.value,
    sandRatioAdj.value,
    alphaAdj.value,
    measuredDensity.value,
  ] as const))

  function clearCalculatedState() {
    calculated.value = emptyCalculatedState()
  }

  function buildTrialSnapshot(): TrialSnapshot {
    return {
      version: 1,
      inputs: {
        batchVolume: batchVolume.value,
        workabilityBinderDelta: workabilityBinderDelta.value,
        workabilitySandRatioDelta: workabilitySandRatioDelta.value,
        workabilityAlphaDelta: workabilityAlphaDelta.value,
        slumpMeasured: slumpMeasured.value,
        spreadMeasured: spreadMeasured.value,
        workabilityOk: workabilityOk.value,
        workabilityNote: workabilityNote.value,
        deltaWb: deltaWb.value,
        deltaBs: deltaBs.value,
        strength0: strength0.value,
        strengthP: strengthP.value,
        strengthN: strengthN.value,
        sTargetStrength: sTargetStrength.value,
        strengthAlpha: strengthAlpha.value,
        strengthMa0: strengthMa0.value,
        strengthMaP: strengthMaP.value,
        strengthMaN: strengthMaN.value,
        wbAdj: wbAdj.value,
        mbAdj: mbAdj.value,
        sandRatioAdj: sandRatioAdj.value,
        alphaAdj: alphaAdj.value,
        measuredDensity: measuredDensity.value,
        strengthGroups: strengthGroups.value.map(g => ({ id: g.id, values: [...g.values] })),
        evalSlump: evalSlump.value,
        evalSpread: evalSpread.value,
        evalWorkabilityDesc: evalWorkabilityDesc.value,
      },
      calculated: calculated.value,
    }
  }

  function applyTrialSnapshot(snapshot: unknown) {
    if (!isPlainObject(snapshot)) {
      return
    }

    const inputs = isPlainObject(snapshot.inputs) ? snapshot.inputs : snapshot

    batchVolume.value = toNumber(inputs.batchVolume, 20)
    workabilityBinderDelta.value = toNumber(inputs.workabilityBinderDelta, 0)
    workabilitySandRatioDelta.value = toNumber(inputs.workabilitySandRatioDelta, 0)
    workabilityAlphaDelta.value = toNumber(inputs.workabilityAlphaDelta, 0)
    slumpMeasured.value = toNullableNumber(inputs.slumpMeasured)
    spreadMeasured.value = toNullableNumber(inputs.spreadMeasured)
    workabilityNote.value = toStringValue(inputs.workabilityNote, '')
    deltaWb.value = toNumber(inputs.deltaWb, 0.02)
    deltaBs.value = toNumber(inputs.deltaBs, 2)
    strength0.value = toNullableNumber(inputs.strength0)
    strengthP.value = toNullableNumber(inputs.strengthP)
    strengthN.value = toNullableNumber(inputs.strengthN)
    sTargetStrength.value = toNullableNumber(inputs.sTargetStrength)
    strengthAlpha.value = toNullableNumber(inputs.strengthAlpha)
    strengthMa0.value = toNullableNumber(inputs.strengthMa0)
    strengthMaP.value = toNullableNumber(inputs.strengthMaP)
    strengthMaN.value = toNullableNumber(inputs.strengthMaN)
    wbAdj.value = toNullableNumber(inputs.wbAdj)
    mbAdj.value = toNullableNumber(inputs.mbAdj)
    sandRatioAdj.value = toNullableNumber(inputs.sandRatioAdj)
    alphaAdj.value = toNullableNumber(inputs.alphaAdj)
    measuredDensity.value = toNullableNumber(inputs.measuredDensity)

    if (Array.isArray(inputs.strengthGroups)) {
      strengthGroups.value = (inputs.strengthGroups as StrengthGroup[]).map(g => ({
        id: g.id,
        values: Array.isArray(g.values) ? g.values.slice(0, 3) : [null, null, null],
      }))
    } else {
      // Backward compat: single evalStrength28d → first group
      const legacy = toNullableNumber(inputs.evalStrength28d)
      if (legacy !== null) {
        strengthGroups.value = [{
          id: 'G01',
          values: [legacy, null, null],
        }, {
          id: 'G02', values: [null, null, null],
        }, {
          id: 'G03', values: [null, null, null],
        }, {
          id: 'G04', values: [null, null, null],
        }, {
          id: 'G05', values: [null, null, null],
        }, {
          id: 'G06', values: [null, null, null],
        }]
      }
    }
    evalSlump.value = toNullableNumber(inputs.evalSlump)
    evalSpread.value = toNullableNumber(inputs.evalSpread)
    evalWorkabilityDesc.value = toStringValue(inputs.evalWorkabilityDesc, '')

    // 试配计算快照来自本界面的上一轮保存，优先直接回填，
    // 随后视图层的防抖重算会再用服务端结果覆盖，保证公式始终以服务端为准。
    if (isPlainObject(snapshot.calculated)) {
      calculated.value = snapshot.calculated as unknown as TrialCalculatedState
    }
  }

  // 后端现在是试配页唯一的业务公式来源，
  // 前端只负责把当前页面状态整理成请求结构并发送给统一接口。
  function buildTrialRequest(): HpcTrialReq | null {
    if (
      wbVal.value === null
      || sandRatioVal.value === null
      || mbVal.value === null
      || mcVal.value === null
      || mgVal.value === null
      || msVal.value === null
      || mwVal.value === null
      || maVal.value === null
      || alphaVal.value === null
    ) {
      return null
    }

    return {
      wb: wbVal.value,
      beta_s: sandRatioVal.value,
      mb: mbVal.value,
      mc: mcVal.value,
      m1: m1Val.value ?? 0,
      m2: m2Val.value ?? 0,
      m3: m3Val.value ?? 0,
      m4: m4Val.value ?? 0,
      mg: mgVal.value,
      ms: msVal.value,
      mw: mwVal.value,
      ma: maVal.value,
      alpha: alphaVal.value,
      batch_volume: batchVolume.value,
      workability_binder_delta: workabilityBinderDelta.value,
      workability_sand_ratio_delta: workabilitySandRatioDelta.value,
      workability_alpha_delta: workabilityAlphaDelta.value,
      delta_wb: deltaWb.value,
      delta_bs: deltaBs.value,
      strength0: strength0.value,
      strength_p: strengthP.value,
      strength_n: strengthN.value,
      target_strength: sTargetStrength.value,
      trial_alpha: strengthAlpha.value,
      trial_ma0: strengthMa0.value,
      trial_maP: strengthMaP.value,
      trial_maN: strengthMaN.value,
      wb_adj: wbAdj.value,
      mb_adj: mbAdj.value,
      sand_ratio_adj: sandRatioAdj.value,
      alpha_adj: alphaAdj.value,
      measured_density: measuredDensity.value,
    }
  }

  async function calcTrial() {
    const requestPayload = buildTrialRequest()
    if (!requestPayload) {
      clearCalculatedState()
      return
    }

    loading.value = true
    error.value = null
    try {
      const response = await calcHpcTrial(requestPayload)
      calculated.value = mapTrialResponse(response)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '高性能试配计算失败'
    } finally {
      loading.value = false
    }
  }

  const workabilityResult = computed(() => calculated.value.workabilityResult)
  const trialMatCols = computed(() => calculated.value.trialMatCols)
  const baseWb = computed(() => calculated.value.baseWb ?? wbVal.value ?? null)
  const baseBs = computed(() => calculated.value.baseBs ?? sandRatioVal.value ?? null)
  const baseAlpha = computed(() => calculated.value.baseAlpha ?? alphaVal.value ?? null)
  const strengthMixes = computed(() => calculated.value.strengthMixes)
  const strengthRegression = computed(() => calculated.value.strengthRegression)
  const chartData = computed(() => calculated.value.chartData)
  const adaptResult = computed(() => calculated.value.adaptResult)
  const calculatedDensity = computed(() => calculated.value.calculatedDensity)
  const densityCorrectionFactor = computed(() => calculated.value.densityCorrectionFactor)
  const labMix = computed(() => calculated.value.labMix)

  function syncDefaults() {
    wbAdj.value = wbVal.value
    mbAdj.value = mbVal.value
    sandRatioAdj.value = sandRatioVal.value
    alphaAdj.value = alphaVal.value
  }

  function syncStrengthDefaults() {
    const defaultStrength = resolveDefaultStrength(store.fcu0)

    if (strength0.value === null) {
      strength0.value = defaultStrength
    }

    if (sTargetStrength.value === null) {
      sTargetStrength.value = defaultStrength
    }
  }

  watch(() => [store.currentRecordId, store.currentTrialData] as const, ([, trialData]) => {
    if (isPlainObject(trialData)) {
      applyTrialSnapshot(trialData)
      return
    }

    resetTrial()

    if (hasData.value) {
      syncDefaults()
      return
    }

    clearCalculatedState()
  }, { immediate: true })

  watch(() => [wbVal.value, mbVal.value, sandRatioVal.value, alphaVal.value, hasData.value] as const, ([, , , , available]) => {
    if (!available) {
      clearCalculatedState()
      return
    }

    if (!hasSavedTrialData.value) {
      syncDefaults()
    }
  }, { immediate: true })

  watch(() => store.fcu0, (value) => {
    if (value === null) {
      return
    }

    syncStrengthDefaults()
  }, { immediate: true })

  function resetWorkability() {
    batchVolume.value = 20
    workabilityBinderDelta.value = 0
    workabilitySandRatioDelta.value = 0
    workabilityAlphaDelta.value = 0
    slumpMeasured.value = null
    spreadMeasured.value = null
    workabilityNote.value = ''
  }

  function resetStrength() {
    deltaWb.value = 0.02
    deltaBs.value = 2
    strength0.value = resolveDefaultStrength(store.fcu0)
    strengthP.value = null
    strengthN.value = null
    sTargetStrength.value = resolveDefaultStrength(store.fcu0)
  }

  function resetCorrection() {
    measuredDensity.value = null
    syncDefaults()
  }

  function resetTrial() {
    resetWorkability()
    resetStrength()
    resetCorrection()
  }

  function applyWorkabilityToCorrection() {
    const result = workabilityResult.value

    if (result.wb === null || result.mb === null || result.bs === null || result.alpha === null) {
      ElMessage.warning('当前没有可同步的工作性实验结果')
      return false
    }

    wbAdj.value = result.wb
    mbAdj.value = result.mb
    sandRatioAdj.value = result.bs
    alphaAdj.value = result.alpha

    ElMessage.success('已同步工作性实验结果')
    return true
  }

  function loadStrengthRecommendation() {
    const regression = strengthRegression.value

    if (regression?.recommendWb === null || regression?.recommendWb === undefined) {
      ElMessage.warning('请先在强度实验中完成回归分析')
      return false
    }

    const recommendedWb = normalizeRecommendedWb(regression.recommendWb)

    if (recommendedWb === null) {
      ElMessage.warning('推荐水胶比无效，请重新进行强度回归分析')
      return false
    }

    wbAdj.value = recommendedWb
    if (workabilityResult.value.mb !== null) {
      mbAdj.value = workabilityResult.value.mb
    }
    if (baseBs.value !== null) {
      sandRatioAdj.value = baseBs.value
    }
    if (baseAlpha.value !== null) {
      alphaAdj.value = baseAlpha.value
    }

    ElMessage.success(`已同步推荐水胶比 ${recommendedWb.toFixed(2)}`)
    return true
  }

  return {
    loading,
    error,
    hasData,
    wbVal,
    strengthGroups,
    strengthOverallAvg,
    strengthMinGroupAvg,
    allGroupsComplete,
    groupResults,
    evalSlump,
    evalSpread,
    evalWorkabilityDesc,
    sandRatioVal,
    mbVal,
    mcVal,
    m1Val,
    m2Val,
    m3Val,
    m4Val,
    mgVal,
    msVal,
    mwVal,
    maVal,
    alphaVal,
    wbAdj,
    mbAdj,
    sandRatioAdj,
    alphaAdj,
    batchVolume,
    workabilityBinderDelta,
    workabilitySandRatioDelta,
    workabilityAlphaDelta,
    slumpMeasured,
    spreadMeasured,
    workabilityOk,
    selectedWorkabilityReference,
    workabilityEvaluation,
    strengthEvaluation,
    workabilityNote,
    buildTrialSnapshot,
    calculationDeps,
    calcTrial,
    clearCalculatedState,
    trialMatCols,
    workabilityResult,
    deltaWb,
    deltaBs,
    strength0,
    strengthP,
    strengthN,
    sTargetStrength,
    strengthAlpha,
    strengthMa0,
    strengthMaP,
    strengthMaN,
    baseWb,
    baseBs,
    strengthMixes,
    strengthRegression,
    chartData,
    adaptResult,
    measuredDensity,
    calculatedDensity,
    densityCorrectionFactor,
    labMix,
    resetWorkability,
    resetStrength,
    resetCorrection,
    resetTrial,
    applyWorkabilityToCorrection,
    loadStrengthRecommendation,
  }
}

export type HpcTrialState = ReturnType<typeof useHpcTrial>