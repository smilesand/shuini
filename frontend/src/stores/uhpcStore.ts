import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getRecordData, getRecordObject } from '../api/records'
import type { UhpcMixReq, UhpcMixRes } from '../api/calc'
import { calcUhpcMix } from '../calc'

type NullableNumber = number | null

export type FiberStrengthGrade = 'UT05' | 'UT07'

export interface UhpcRatios {
  cement: NullableNumber
  flyAsh: NullableNumber
  microBead: NullableNumber
  silicaFume: NullableNumber
}

export interface UhpcMaterialMasses {
  binder: NullableNumber
  cement: NullableNumber
  flyAsh: NullableNumber
  microBead: NullableNumber
  silicaFume: NullableNumber
  sand: NullableNumber
  steelFiber: NullableNumber
  water: NullableNumber
  admixture: NullableNumber
  total: NullableNumber
}

export interface UhpcCalculatedState {
  designStrength: NullableNumber
  binderVolumeRatios: UhpcRatios
  binderMassRatios: {
    initial: UhpcRatios
    corrected: UhpcRatios
  }
  materialMasses: UhpcMaterialMasses
}

interface UhpcInputSnapshot {
  strengthGrade: NullableNumber
  waterBinderRatio: NullableNumber
  admixtureRatio: NullableNumber
  sandBinderRatio: NullableNumber
  steelFiberVolumeRatio: NullableNumber
  fiberStrengthGrade: FiberStrengthGrade
  maxParticleSize: NullableNumber
  minParticleSize: NullableNumber
  distributionIndex: NullableNumber
  flyAshPeakSize: NullableNumber
  flyAshAccumulationSize: NullableNumber
  microBeadPeakSize: NullableNumber
  microBeadSilicaFumeRatio: NullableNumber
  cementDensity: NullableNumber
  flyAshDensity: NullableNumber
  microBeadDensity: NullableNumber
  silicaFumeDensity: NullableNumber
  microPowderCoefficient: NullableNumber
  assumedMixMass: NullableNumber
  steelFiberDensity: number
}

export interface UhpcSnapshot {
  version: number
  inputs: UhpcInputSnapshot
  calculated: UhpcCalculatedState
}

export const UHPC_INPUT_PLACEHOLDERS = {
  strengthGrade: '130',
  waterBinderRatio: '0.19',
  admixtureRatio: '1.8',
  sandBinderRatio: '1.20',
  steelFiberVolumeRatio: '1.8',
  maxParticleSize: '80',
  minParticleSize: '1',
  distributionIndex: '0.22',
  flyAshPeakSize: '18',
  flyAshAccumulationSize: '8',
  microBeadPeakSize: '4',
  microBeadSilicaFumeRatio: '0.50',
  cementDensity: '3100',
  flyAshDensity: '2300',
  microBeadDensity: '2600',
  silicaFumeDensity: '2200',
  microPowderCoefficient: '0.55',
  assumedMixMass: '2500',
} as const

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function toNullableNumber(value: unknown): NullableNumber {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function toNumber(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function toFiberStrengthGrade(value: unknown): FiberStrengthGrade {
  return value === 'UT07' ? 'UT07' : 'UT05'
}

function emptyRatios(): UhpcRatios {
  return {
    cement: null,
    flyAsh: null,
    microBead: null,
    silicaFume: null,
  }
}

function emptyMaterialMasses(): UhpcMaterialMasses {
  return {
    binder: null,
    cement: null,
    flyAsh: null,
    microBead: null,
    silicaFume: null,
    sand: null,
    steelFiber: null,
    water: null,
    admixture: null,
    total: null,
  }
}

function emptyCalculatedState(): UhpcCalculatedState {
  return {
    designStrength: null,
    binderVolumeRatios: emptyRatios(),
    binderMassRatios: {
      initial: emptyRatios(),
      corrected: emptyRatios(),
    },
    materialMasses: emptyMaterialMasses(),
  }
}

function mapRatios(result: UhpcMixRes['binder_volume_ratios']): UhpcRatios {
  return {
    cement: result.cement,
    flyAsh: result.fly_ash,
    microBead: result.micro_bead,
    silicaFume: result.silica_fume,
  }
}

function mapMaterialMasses(result: UhpcMixRes['material_masses']): UhpcMaterialMasses {
  return {
    binder: result.binder,
    cement: result.cement,
    flyAsh: result.fly_ash,
    microBead: result.micro_bead,
    silicaFume: result.silica_fume,
    sand: result.sand,
    steelFiber: result.steel_fiber,
    water: result.water,
    admixture: result.admixture,
    total: result.total,
  }
}

function mapUhpcResponse(response: UhpcMixRes): UhpcCalculatedState {
  return {
    designStrength: response.design_strength,
    binderVolumeRatios: mapRatios(response.binder_volume_ratios),
    binderMassRatios: {
      initial: mapRatios(response.binder_mass_ratios.initial),
      corrected: mapRatios(response.binder_mass_ratios.corrected),
    },
    materialMasses: mapMaterialMasses(response.material_masses),
  }
}

function packingFraction(
  particleSize: number,
  maxParticleSize: number,
  minParticleSize: number,
  distributionIndex: number,
): number {
  const denominator = (maxParticleSize ** distributionIndex) - (minParticleSize ** distributionIndex)
  if (denominator <= 0) {
    throw new Error('体系最大粒径必须大于体系最小粒径')
  }
  if (particleSize <= minParticleSize) {
    throw new Error('参与计算的粒径必须大于体系最小粒径')
  }

  return ((particleSize ** distributionIndex) - (minParticleSize ** distributionIndex)) / denominator * 100
}

function validateUhpcPayload(payload: UhpcMixReq): string | null {
  try {
    if (payload.max_particle_size <= payload.min_particle_size) {
      return '体系最大粒径必须大于体系最小粒径'
    }
    if (payload.distribution_index <= 0) {
      return '粒径分布指数必须大于 0'
    }
    if (payload.fly_ash_peak_size - payload.fly_ash_accumulation_size <= payload.min_particle_size) {
      return '粉煤灰峰值粒径减堆积粒径后必须大于体系最小粒径'
    }
    if (!(payload.micro_bead_silica_fume_ratio > 0 && payload.micro_bead_silica_fume_ratio < 1)) {
      return '微珠占硅灰、微粉的比例必须在 0~1 之间'
    }
    if (payload.micro_powder_coefficient <= 0) {
      return '微粉系数必须大于 0'
    }
    if (payload.assumed_mix_mass <= 0) {
      return '假定拌合物质量必须大于 0'
    }
    if (payload.steel_fiber_density <= 0) {
      return '钢纤维密度必须大于 0'
    }

    const flyAshVolumeRatio = (
      packingFraction(
        payload.fly_ash_peak_size + payload.fly_ash_accumulation_size,
        payload.max_particle_size,
        payload.min_particle_size,
        payload.distribution_index,
      )
      - packingFraction(
        payload.fly_ash_peak_size - payload.fly_ash_accumulation_size,
        payload.max_particle_size,
        payload.min_particle_size,
        payload.distribution_index,
      )
    )
    const microPowderVolumeRatio = packingFraction(
      payload.micro_bead_peak_size,
      payload.max_particle_size,
      payload.min_particle_size,
      payload.distribution_index,
    )
    const microBeadVolumeRatio = microPowderVolumeRatio * payload.micro_bead_silica_fume_ratio
    const silicaFumeVolumeRatio = microPowderVolumeRatio * (1 - payload.micro_bead_silica_fume_ratio)
    const cementVolumeRatio = 100 - flyAshVolumeRatio - microBeadVolumeRatio - silicaFumeVolumeRatio

    if (cementVolumeRatio <= 0) {
      return '计算后的水泥体积比例不合法，请检查粒径参数'
    }

    const massRatioDenominator = (
      cementVolumeRatio * payload.cement_density
      + flyAshVolumeRatio * payload.fly_ash_density
      + microBeadVolumeRatio * payload.micro_bead_density
      + silicaFumeVolumeRatio * payload.silica_fume_density
    )
    if (massRatioDenominator <= 0) {
      return '胶凝材料质量比例分母必须大于 0'
    }

    const initialCementMassRatio = (cementVolumeRatio * payload.cement_density / massRatioDenominator) * 100
    const initialMicroBeadMassRatio = (microBeadVolumeRatio * payload.micro_bead_density / massRatioDenominator) * 100
    const initialSilicaFumeMassRatio = (silicaFumeVolumeRatio * payload.silica_fume_density / massRatioDenominator) * 100
    const correctedCementMassRatio = (
      initialCementMassRatio
      + initialSilicaFumeMassRatio
      - initialSilicaFumeMassRatio * payload.micro_powder_coefficient
      + initialMicroBeadMassRatio
      - initialMicroBeadMassRatio * payload.micro_powder_coefficient
    )

    if (correctedCementMassRatio <= 0) {
      return '修正后的水泥质量比例不合法，请检查微粉系数'
    }

    const steelFiberMass = (payload.steel_fiber_volume_ratio / 100) * payload.steel_fiber_density
    const alphaFraction = payload.admixture_ratio / 100
    const binderMass = (payload.assumed_mix_mass - steelFiberMass) /
      (1 + payload.sand_binder_ratio + payload.water_binder_ratio + alphaFraction)

    if (binderMass <= 0) {
      return '计算得到的胶凝材料总量不合法，请检查钢纤维体积掺量或总质量'
    }

    return null
  } catch (error: unknown) {
    return error instanceof Error ? error.message : 'UHPC 参数校验失败'
  }
}

export const useUhpcStore = defineStore('uhpc', () => {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastCalcSignature = ref('')

  const currentRecordId = ref<number | null>(null)
  const currentRecordName = ref('')
  const currentRecordProjectId = ref<number | null>(null)
  const currentDesignData = ref<object | null>(null)
  const currentTrialData = ref<object | null>(null)

  const uhpcSelectedProjectId = ref<number | null>(null)
  const uhpcShowCalculator = ref(false)

  const strengthGrade = ref<NullableNumber>(null)
  const waterBinderRatio = ref<NullableNumber>(null)
  const admixtureRatio = ref<NullableNumber>(null)
  const sandBinderRatio = ref<NullableNumber>(null)
  const steelFiberVolumeRatio = ref<NullableNumber>(null)
  const fiberStrengthGrade = ref<FiberStrengthGrade>('UT05')

  // UI-only helper fields for auto-suggesting W/B and S/B (not sent to backend)
  const cementStrength = ref<NullableNumber>(null)       // 水泥 28d 抗压强度 (MPa)
  const silicaActivity = ref<NullableNumber>(null)       // 硅灰活性指数 (%)
  const sandCrushValue = ref<NullableNumber>(null)       // 砂压碎值 (%)
  const hasHardeningRequirement = ref(false)             // 是否有应变硬化需求

  const maxParticleSize = ref<NullableNumber>(null)
  const minParticleSize = ref<NullableNumber>(null)
  const distributionIndex = ref<NullableNumber>(null)
  const flyAshPeakSize = ref<NullableNumber>(null)
  const flyAshAccumulationSize = ref<NullableNumber>(null)
  const microBeadPeakSize = ref<NullableNumber>(null)
  const microBeadSilicaFumeRatio = ref<NullableNumber>(null)

  const cementDensity = ref<NullableNumber>(null)
  const flyAshDensity = ref<NullableNumber>(null)
  const microBeadDensity = ref<NullableNumber>(null)
  const silicaFumeDensity = ref<NullableNumber>(null)
  const microPowderCoefficient = ref<NullableNumber>(null)

  const assumedMixMass = ref<NullableNumber>(null)
  const steelFiberDensity = ref(7850)
  const calculated = ref<UhpcCalculatedState>(emptyCalculatedState())

  const designStrength = computed(() => {
    if (calculated.value.designStrength !== null) {
      return calculated.value.designStrength
    }

    if (strengthGrade.value === null) {
      return null
    }

    return Number((strengthGrade.value * 1.1).toFixed(2))
  })

  const binderVolumeRatios = computed(() => calculated.value.binderVolumeRatios)
  const binderMassRatios = computed(() => calculated.value.binderMassRatios)
  const materialMasses = computed(() => calculated.value.materialMasses)
  const hasResults = computed(() => calculated.value.materialMasses.total !== null)
  const hasRequiredInputs = computed(() => (
    strengthGrade.value !== null
    && waterBinderRatio.value !== null
    && admixtureRatio.value !== null
    && sandBinderRatio.value !== null
    && steelFiberVolumeRatio.value !== null
    && maxParticleSize.value !== null
    && minParticleSize.value !== null
    && distributionIndex.value !== null
    && flyAshPeakSize.value !== null
    && flyAshAccumulationSize.value !== null
    && microBeadPeakSize.value !== null
    && microBeadSilicaFumeRatio.value !== null
    && cementDensity.value !== null
    && flyAshDensity.value !== null
    && microBeadDensity.value !== null
    && silicaFumeDensity.value !== null
    && microPowderCoefficient.value !== null
    && assumedMixMass.value !== null
  ))

  const calculationDeps = computed(() => ([
    strengthGrade.value,
    waterBinderRatio.value,
    admixtureRatio.value,
    sandBinderRatio.value,
    steelFiberVolumeRatio.value,
    fiberStrengthGrade.value,
    maxParticleSize.value,
    minParticleSize.value,
    distributionIndex.value,
    flyAshPeakSize.value,
    flyAshAccumulationSize.value,
    microBeadPeakSize.value,
    microBeadSilicaFumeRatio.value,
    cementDensity.value,
    flyAshDensity.value,
    microBeadDensity.value,
    silicaFumeDensity.value,
    microPowderCoefficient.value,
    assumedMixMass.value,
    steelFiberDensity.value,
  ] as const))

  function setCurrentRecord(recordId: number | null, name = '', projectId: number | null = null) {
    currentRecordId.value = recordId
    currentRecordName.value = name
    currentRecordProjectId.value = projectId
  }

  function markRecordSaved(recordId: number, name: string, projectId: number | null = null) {
    setCurrentRecord(recordId, name, projectId)
  }

  function setCurrentDesignData(designData: object | null) {
    currentDesignData.value = designData
  }

  function setCurrentTrialData(trialData: object | null) {
    currentTrialData.value = trialData
  }

  function setUhpcProjectState(projectId: number | null, showCalculatorVisible = uhpcShowCalculator.value) {
    uhpcSelectedProjectId.value = projectId
    uhpcShowCalculator.value = showCalculatorVisible
  }

  function clearUhpcProjectState() {
    setUhpcProjectState(null, false)
  }

  function clearCalculatedState() {
    calculated.value = emptyCalculatedState()
  }

  function buildRequest(): UhpcMixReq | null {
    if (
      strengthGrade.value === null
      || waterBinderRatio.value === null
      || admixtureRatio.value === null
      || sandBinderRatio.value === null
      || steelFiberVolumeRatio.value === null
      || maxParticleSize.value === null
      || minParticleSize.value === null
      || distributionIndex.value === null
      || flyAshPeakSize.value === null
      || flyAshAccumulationSize.value === null
      || microBeadPeakSize.value === null
      || microBeadSilicaFumeRatio.value === null
      || cementDensity.value === null
      || flyAshDensity.value === null
      || microBeadDensity.value === null
      || silicaFumeDensity.value === null
      || microPowderCoefficient.value === null
      || assumedMixMass.value === null
    ) {
      return null
    }

    return {
      strength_grade: strengthGrade.value,
      water_binder_ratio: waterBinderRatio.value,
      admixture_ratio: admixtureRatio.value,
      sand_binder_ratio: sandBinderRatio.value,
      steel_fiber_volume_ratio: steelFiberVolumeRatio.value,
      max_particle_size: maxParticleSize.value,
      min_particle_size: minParticleSize.value,
      distribution_index: distributionIndex.value,
      fly_ash_peak_size: flyAshPeakSize.value,
      fly_ash_accumulation_size: flyAshAccumulationSize.value,
      micro_bead_peak_size: microBeadPeakSize.value,
      micro_bead_silica_fume_ratio: microBeadSilicaFumeRatio.value,
      cement_density: cementDensity.value,
      fly_ash_density: flyAshDensity.value,
      micro_bead_density: microBeadDensity.value,
      silica_fume_density: silicaFumeDensity.value,
      micro_powder_coefficient: microPowderCoefficient.value,
      assumed_mix_mass: assumedMixMass.value,
      steel_fiber_density: steelFiberDensity.value,
    }
  }

  async function calcMix() {
    const payload = buildRequest()
    if (!payload) {
      error.value = null
      lastCalcSignature.value = ''
      clearCalculatedState()
      return
    }

    const signature = JSON.stringify(payload)
    const validationError = validateUhpcPayload(payload)

    if (signature === lastCalcSignature.value) {
      if (validationError) {
        error.value = validationError
      }
      return
    }

    lastCalcSignature.value = signature

    if (validationError) {
      clearCalculatedState()
      error.value = validationError
      return
    }

    error.value = null
    try {
      // 改为前端引擎同步计算（src/calc），服务端仅用于数据持久化。
      const response = calcUhpcMix(payload)
      assumedMixMass.value = response.assumed_mix_mass
      steelFiberDensity.value = response.steel_fiber_density
      calculated.value = mapUhpcResponse(response)
    } catch (e: unknown) {
      clearCalculatedState()
      error.value = e instanceof Error ? e.message : 'UHPC 配合比计算失败'
    } finally {
      loading.value = false
    }
  }

  function buildDesignSnapshot(): UhpcSnapshot {
    return {
      version: 1,
      inputs: {
        strengthGrade: strengthGrade.value,
        waterBinderRatio: waterBinderRatio.value,
        admixtureRatio: admixtureRatio.value,
        sandBinderRatio: sandBinderRatio.value,
        steelFiberVolumeRatio: steelFiberVolumeRatio.value,
        fiberStrengthGrade: fiberStrengthGrade.value,
        maxParticleSize: maxParticleSize.value,
        minParticleSize: minParticleSize.value,
        distributionIndex: distributionIndex.value,
        flyAshPeakSize: flyAshPeakSize.value,
        flyAshAccumulationSize: flyAshAccumulationSize.value,
        microBeadPeakSize: microBeadPeakSize.value,
        microBeadSilicaFumeRatio: microBeadSilicaFumeRatio.value,
        cementDensity: cementDensity.value,
        flyAshDensity: flyAshDensity.value,
        microBeadDensity: microBeadDensity.value,
        silicaFumeDensity: silicaFumeDensity.value,
        microPowderCoefficient: microPowderCoefficient.value,
        assumedMixMass: assumedMixMass.value,
        steelFiberDensity: steelFiberDensity.value,
      },
      calculated: calculated.value,
    }
  }

  function applySnapshot(snapshot: unknown) {
    if (!isPlainObject(snapshot)) {
      return
    }

    const inputs = isPlainObject(snapshot.inputs) ? snapshot.inputs : snapshot

    strengthGrade.value = toNullableNumber(inputs.strengthGrade)
    waterBinderRatio.value = toNullableNumber(inputs.waterBinderRatio)
    admixtureRatio.value = toNullableNumber(inputs.admixtureRatio)
    sandBinderRatio.value = toNullableNumber(inputs.sandBinderRatio)
    steelFiberVolumeRatio.value = toNullableNumber(inputs.steelFiberVolumeRatio)
    fiberStrengthGrade.value = toFiberStrengthGrade(inputs.fiberStrengthGrade)
    maxParticleSize.value = toNullableNumber(inputs.maxParticleSize)
    minParticleSize.value = toNullableNumber(inputs.minParticleSize)
    distributionIndex.value = toNullableNumber(inputs.distributionIndex)
    flyAshPeakSize.value = toNullableNumber(inputs.flyAshPeakSize)
    flyAshAccumulationSize.value = toNullableNumber(inputs.flyAshAccumulationSize)
    microBeadPeakSize.value = toNullableNumber(inputs.microBeadPeakSize)
    microBeadSilicaFumeRatio.value = toNullableNumber(inputs.microBeadSilicaFumeRatio)
    cementDensity.value = toNullableNumber(inputs.cementDensity)
    flyAshDensity.value = toNullableNumber(inputs.flyAshDensity)
    microBeadDensity.value = toNullableNumber(inputs.microBeadDensity)
    silicaFumeDensity.value = toNullableNumber(inputs.silicaFumeDensity)
    microPowderCoefficient.value = toNullableNumber(inputs.microPowderCoefficient)
    assumedMixMass.value = toNullableNumber(inputs.assumedMixMass)
    steelFiberDensity.value = toNumber(inputs.steelFiberDensity, 7850)

    if (isPlainObject(snapshot.calculated)) {
      calculated.value = snapshot.calculated as unknown as UhpcCalculatedState
    }
  }

  function applyRecordData(record: Record<string, unknown>) {
    resetAll()

    const recordId = typeof record.id === 'number' ? record.id : null
    const recordName = typeof record.name === 'string' ? record.name : ''
    const recordProjectId = typeof record.project_id === 'number' ? record.project_id : null
    const recordData = getRecordData(record)
    const designData = getRecordObject(record, 'design_data')

    setCurrentRecord(recordId, recordName, recordProjectId)
    setCurrentDesignData(
      designData && typeof designData === 'object' && !Array.isArray(designData)
        ? designData as object
        : null,
    )
    setCurrentTrialData(
      getRecordObject(record, 'trial_data')
      ?? (designData && typeof designData === 'object' && !Array.isArray(designData) ? designData as object : null),
    )

    if (designData && typeof designData === 'object' && !Array.isArray(designData)) {
      applySnapshot(designData)
      return
    }

    if (recordData.fcuk != null) strengthGrade.value = Number(recordData.fcuk)
    if (recordData.wb != null) waterBinderRatio.value = Number(recordData.wb)
    if (recordData.alpha != null) admixtureRatio.value = Number(recordData.alpha)
    if (recordData.sand_ratio != null) sandBinderRatio.value = Number(recordData.sand_ratio)
    if (recordData.mb != null) calculated.value.materialMasses.binder = Number(recordData.mb)
    if (recordData.mc != null) calculated.value.materialMasses.cement = Number(recordData.mc)
    if (recordData.m1 != null) calculated.value.materialMasses.flyAsh = Number(recordData.m1)
    if (recordData.m3 != null) calculated.value.materialMasses.microBead = Number(recordData.m3)
    if (recordData.m4 != null) calculated.value.materialMasses.silicaFume = Number(recordData.m4)
    if (recordData.ms != null) calculated.value.materialMasses.sand = Number(recordData.ms)
    if (recordData.mw != null) calculated.value.materialMasses.water = Number(recordData.mw)
    if (recordData.ma != null) calculated.value.materialMasses.admixture = Number(recordData.ma)
    if (recordData.total_mass != null) calculated.value.materialMasses.total = Number(recordData.total_mass)
    if (recordData.fcu0 != null) calculated.value.designStrength = Number(recordData.fcu0)
  }

  /** 从 Excel 导入数据直接载入（支持 Excel 导出格式的字段名映射） */
  function importFromExcel(data: Record<string, unknown>) {
    resetAll()

    // ── 基本信息 ──
    const name = typeof data.record_name === 'string' ? data.record_name : ''
    setCurrentRecord(null, name, null)

    // ── 主要参数（兼容 Excel 导出字段名） ──
    if (data.strength_grade != null) strengthGrade.value = Number(data.strength_grade)
    else if (data.fcuk != null) strengthGrade.value = Number(data.fcuk)

    if (data.water_binder_ratio != null) waterBinderRatio.value = Number(data.water_binder_ratio)
    else if (data.wb != null) waterBinderRatio.value = Number(data.wb)

    if (data.admixture_ratio != null) admixtureRatio.value = Number(data.admixture_ratio)
    else if (data.alpha != null) admixtureRatio.value = Number(data.alpha)

    if (data.sand_binder_ratio != null) sandBinderRatio.value = Number(data.sand_binder_ratio)
    else if (data.sand_ratio != null) sandBinderRatio.value = Number(data.sand_ratio)

    if (data.steel_fiber_volume_ratio != null) steelFiberVolumeRatio.value = Number(data.steel_fiber_volume_ratio)
    if (data.fiber_strength_grade != null) fiberStrengthGrade.value = toFiberStrengthGrade(data.fiber_strength_grade)

    // ── 粒径分布 ──
    if (data.max_particle_size != null) maxParticleSize.value = Number(data.max_particle_size)
    if (data.min_particle_size != null) minParticleSize.value = Number(data.min_particle_size)
    if (data.distribution_index != null) distributionIndex.value = Number(data.distribution_index)
    if (data.fly_ash_peak_size != null) flyAshPeakSize.value = Number(data.fly_ash_peak_size)
    if (data.fly_ash_accumulation_size != null) flyAshAccumulationSize.value = Number(data.fly_ash_accumulation_size)
    if (data.micro_bead_peak_size != null) microBeadPeakSize.value = Number(data.micro_bead_peak_size)
    if (data.micro_bead_silica_fume_ratio != null) microBeadSilicaFumeRatio.value = Number(data.micro_bead_silica_fume_ratio)

    // ── 密度参数 ──
    if (data.cement_density != null) cementDensity.value = Number(data.cement_density)
    if (data.fly_ash_density != null) flyAshDensity.value = Number(data.fly_ash_density)
    if (data.micro_bead_density != null) microBeadDensity.value = Number(data.micro_bead_density)
    if (data.silica_fume_density != null) silicaFumeDensity.value = Number(data.silica_fume_density)
    if (data.micro_powder_coefficient != null) microPowderCoefficient.value = Number(data.micro_powder_coefficient)
    if (data.assumed_mix_mass != null) assumedMixMass.value = Number(data.assumed_mix_mass)
    if (data.steel_fiber_density != null) steelFiberDensity.value = Number(data.steel_fiber_density)
  }

  function buildRecordPayload(
    name: string,
    projectId: number | null = null,
    recordId: number | null = currentRecordId.value,
  ) {
    const snapshot = buildDesignSnapshot()

    return {
      ...(recordId !== null ? { id: recordId } : {}),
      name,
      category: 'uhpc',
      project_id: projectId,
      record_data: {
        fcuk: strengthGrade.value,
        fcu0: designStrength.value,
        wb: waterBinderRatio.value,
        sand_ratio: sandBinderRatio.value,
        mb: materialMasses.value.binder,
        mc: materialMasses.value.cement,
        m1: materialMasses.value.flyAsh,
        m3: materialMasses.value.microBead,
        m4: materialMasses.value.silicaFume,
        ms: materialMasses.value.sand,
        alpha: admixtureRatio.value,
        mw: materialMasses.value.water,
        ma: materialMasses.value.admixture,
        total_mass: materialMasses.value.total,
        design_data: snapshot,
      },
    }
  }

  function resetAll() {
    loading.value = false
    error.value = null
    lastCalcSignature.value = ''
    setCurrentRecord(null)
    setCurrentDesignData(null)
    setCurrentTrialData(null)

    strengthGrade.value = null
    waterBinderRatio.value = null
    admixtureRatio.value = null
    sandBinderRatio.value = null
    steelFiberVolumeRatio.value = null
    fiberStrengthGrade.value = 'UT05'

    cementStrength.value = null
    silicaActivity.value = null
    sandCrushValue.value = null
    hasHardeningRequirement.value = false

    maxParticleSize.value = null
    minParticleSize.value = null
    distributionIndex.value = null
    flyAshPeakSize.value = null
    flyAshAccumulationSize.value = null
    microBeadPeakSize.value = null
    microBeadSilicaFumeRatio.value = null

    cementDensity.value = null
    flyAshDensity.value = null
    microBeadDensity.value = null
    silicaFumeDensity.value = null
    microPowderCoefficient.value = null

    assumedMixMass.value = null
    steelFiberDensity.value = 7850
    clearCalculatedState()
  }

  return {
    loading,
    error,
    currentRecordId,
    currentRecordName,
    currentRecordProjectId,
    currentDesignData,
    currentTrialData,
    uhpcSelectedProjectId,
    uhpcShowCalculator,
    strengthGrade,
    waterBinderRatio,
    admixtureRatio,
    sandBinderRatio,
    steelFiberVolumeRatio,
    fiberStrengthGrade,
    cementStrength,
    silicaActivity,
    sandCrushValue,
    hasHardeningRequirement,
    maxParticleSize,
    minParticleSize,
    distributionIndex,
    flyAshPeakSize,
    flyAshAccumulationSize,
    microBeadPeakSize,
    microBeadSilicaFumeRatio,
    cementDensity,
    flyAshDensity,
    microBeadDensity,
    silicaFumeDensity,
    microPowderCoefficient,
    assumedMixMass,
    steelFiberDensity,
    designStrength,
    binderVolumeRatios,
    binderMassRatios,
    materialMasses,
    hasResults,
    hasRequiredInputs,
    calculationDeps,
    setCurrentRecord,
    markRecordSaved,
    setCurrentDesignData,
    setCurrentTrialData,
    setUhpcProjectState,
    clearUhpcProjectState,
    clearCalculatedState,
    calcMix,
    buildDesignSnapshot,
    applyRecordData,
    importFromExcel,
    buildRecordPayload,
    resetAll,
  }
})