/**
 * calc/uhpc.ts
 * ============
 * 超高性能混凝土（UHPC）配合比计算引擎，由后端 services/uhpc.py 迁移而来。
 *
 * 复刻 PDF/PPT 中 4.5.1~4.5.7、4.7.1 的设计公式：
 *   1. 按 Andreasen 堆积模型由粒径求各胶材体积比例
 *   2. 体积比例 → 初始质量比例 → 微粉系数修正后的质量比例
 *   3. 由假定拌合物质量反算胶材总量及各材料每方用量
 *
 * 舍入：后端 `_round_js`（floor(x·f+0.5)/f）→ 前端 jsRound。
 */
import { jsRound } from './rounding'
import type {
  UhpcMixReq,
  UhpcMixRes,
  UhpcRatioRes,
} from '../api/calc'

export const DEFAULT_ASSUMED_MIX_MASS = 2500.0
export const DEFAULT_STEEL_FIBER_DENSITY = 7850.0

/**
 * Andreasen 堆积分数：返回某粒径对应的累计体积分数（百分制）。
 * 该实现需与后端 _packing_fraction 完全一致。
 */
export function packingFraction(
  particleSize: number,
  maxParticleSize: number,
  minParticleSize: number,
  distributionIndex: number,
): number {
  const denominator =
    maxParticleSize ** distributionIndex - minParticleSize ** distributionIndex
  if (denominator <= 0) throw new Error('粒径上限必须大于粒径下限')
  if (particleSize <= minParticleSize) throw new Error('参与计算的粒径必须大于体系最小粒径')
  const numerator = particleSize ** distributionIndex - minParticleSize ** distributionIndex
  return (numerator / denominator) * 100.0
}

function buildRatioResult(
  cement: number,
  flyAsh: number,
  microBead: number,
  silicaFume: number,
  digits = 2,
): UhpcRatioRes {
  return {
    cement: jsRound(cement, digits),
    fly_ash: jsRound(flyAsh, digits),
    micro_bead: jsRound(microBead, digits),
    silica_fume: jsRound(silicaFume, digits),
  }
}

/** UHPC 配合比完整计算，输入/输出与后端 calc_uhpc_mix 一致。 */
export function calcUhpcMix(req: UhpcMixReq): UhpcMixRes {
  const {
    strength_grade: strengthGrade,
    water_binder_ratio: waterBinderRatio,
    admixture_ratio: admixtureRatio,
    sand_binder_ratio: sandBinderRatio,
    steel_fiber_volume_ratio: steelFiberVolumeRatio,
    max_particle_size: maxParticleSize,
    min_particle_size: minParticleSize,
    distribution_index: distributionIndex,
    fly_ash_peak_size: flyAshPeakSize,
    fly_ash_accumulation_size: flyAshAccumulationSize,
    micro_bead_peak_size: microBeadPeakSize,
    micro_bead_silica_fume_ratio: microBeadSilicaFumeRatio,
    cement_density: cementDensity,
    fly_ash_density: flyAshDensity,
    micro_bead_density: microBeadDensity,
    silica_fume_density: silicaFumeDensity,
    micro_powder_coefficient: microPowderCoefficient,
    assumed_mix_mass: assumedMixMass,
    steel_fiber_density: steelFiberDensity,
  } = req

  if (strengthGrade <= 0) throw new Error('强度等级必须大于 0')
  if (waterBinderRatio <= 0) throw new Error('水胶比必须大于 0')
  if (sandBinderRatio <= 0) throw new Error('砂胶比必须大于 0')
  if (!(admixtureRatio >= 0 && admixtureRatio < 100)) throw new Error('外加剂掺量必须在 0~100% 之间')
  if (!(steelFiberVolumeRatio >= 0 && steelFiberVolumeRatio < 100)) {
    throw new Error('钢纤维体积掺量必须在 0~100% 之间')
  }
  if (maxParticleSize <= minParticleSize) throw new Error('体系最大粒径必须大于体系最小粒径')
  if (distributionIndex <= 0) throw new Error('粒径分布指数必须大于 0')
  if (flyAshPeakSize <= 0 || flyAshAccumulationSize <= 0 || microBeadPeakSize <= 0) {
    throw new Error('峰值粒径和堆积粒径必须大于 0')
  }
  if (flyAshPeakSize - flyAshAccumulationSize <= minParticleSize) {
    throw new Error('粉煤灰峰值粒径减堆积粒径后必须大于体系最小粒径')
  }
  if (!(microBeadSilicaFumeRatio > 0 && microBeadSilicaFumeRatio < 1)) {
    throw new Error('微珠占硅灰、微粉的比例必须在 0~1 之间')
  }
  if (cementDensity <= 0 || flyAshDensity <= 0 || microBeadDensity <= 0 || silicaFumeDensity <= 0) {
    throw new Error('材料密度必须大于 0')
  }
  if (microPowderCoefficient <= 0) throw new Error('微粉系数必须大于 0')
  if (assumedMixMass <= 0) throw new Error('假定拌合物质量必须大于 0')
  if (steelFiberDensity <= 0) throw new Error('钢纤维密度必须大于 0')

  const designStrength = strengthGrade * 1.1

  const flyAshVolumeRatio =
    packingFraction(flyAshPeakSize + flyAshAccumulationSize, maxParticleSize, minParticleSize, distributionIndex) -
    packingFraction(flyAshPeakSize - flyAshAccumulationSize, maxParticleSize, minParticleSize, distributionIndex)
  const microPowderVolumeRatio = packingFraction(
    microBeadPeakSize, maxParticleSize, minParticleSize, distributionIndex,
  )
  const microBeadVolumeRatio = microPowderVolumeRatio * microBeadSilicaFumeRatio
  const silicaFumeVolumeRatio = microPowderVolumeRatio * (1.0 - microBeadSilicaFumeRatio)
  const cementVolumeRatio = 100.0 - flyAshVolumeRatio - microBeadVolumeRatio - silicaFumeVolumeRatio

  if (cementVolumeRatio <= 0) throw new Error('计算后的水泥体积比例不合法，请检查粒径参数')

  const massRatioDenominator =
    cementVolumeRatio * cementDensity +
    flyAshVolumeRatio * flyAshDensity +
    microBeadVolumeRatio * microBeadDensity +
    silicaFumeVolumeRatio * silicaFumeDensity
  if (massRatioDenominator <= 0) throw new Error('胶凝材料质量比例分母必须大于 0')

  const initialCementMassRatio = (cementVolumeRatio * cementDensity / massRatioDenominator) * 100.0
  const initialFlyAshMassRatio = (flyAshVolumeRatio * flyAshDensity / massRatioDenominator) * 100.0
  const initialMicroBeadMassRatio = (microBeadVolumeRatio * microBeadDensity / massRatioDenominator) * 100.0
  const initialSilicaFumeMassRatio = (silicaFumeVolumeRatio * silicaFumeDensity / massRatioDenominator) * 100.0

  const correctedSilicaFumeMassRatio = initialSilicaFumeMassRatio * microPowderCoefficient
  const correctedMicroBeadMassRatio = initialMicroBeadMassRatio * microPowderCoefficient
  const correctedCementMassRatio =
    initialCementMassRatio +
    initialSilicaFumeMassRatio - correctedSilicaFumeMassRatio +
    initialMicroBeadMassRatio - correctedMicroBeadMassRatio

  if (correctedCementMassRatio <= 0) throw new Error('修正后的水泥质量比例不合法，请检查微粉系数')

  const steelFiberMass = (steelFiberVolumeRatio / 100.0) * steelFiberDensity
  const alphaFraction = admixtureRatio / 100.0
  const binderMass =
    (assumedMixMass - steelFiberMass) / (1.0 + sandBinderRatio + waterBinderRatio + alphaFraction)

  if (binderMass <= 0) throw new Error('计算得到的胶凝材料总量不合法，请检查钢纤维体积掺量或总质量')

  const sandMass = binderMass * sandBinderRatio
  const waterMass = binderMass * waterBinderRatio
  const admixtureMass = binderMass * alphaFraction
  const cementMass = binderMass * (correctedCementMassRatio / 100.0)
  const flyAshMass = binderMass * (initialFlyAshMassRatio / 100.0)
  const microBeadMass = binderMass * (correctedMicroBeadMassRatio / 100.0)
  const silicaFumeMass = binderMass * (correctedSilicaFumeMassRatio / 100.0)
  const totalMass = binderMass + sandMass + waterMass + admixtureMass + steelFiberMass

  return {
    design_strength: jsRound(designStrength, 2),
    assumed_mix_mass: jsRound(assumedMixMass, 2),
    steel_fiber_density: jsRound(steelFiberDensity, 2),
    binder_volume_ratios: buildRatioResult(
      cementVolumeRatio, flyAshVolumeRatio, microBeadVolumeRatio, silicaFumeVolumeRatio,
    ),
    binder_mass_ratios: {
      initial: buildRatioResult(
        initialCementMassRatio, initialFlyAshMassRatio, initialMicroBeadMassRatio, initialSilicaFumeMassRatio,
      ),
      corrected: buildRatioResult(
        correctedCementMassRatio, initialFlyAshMassRatio, correctedMicroBeadMassRatio, correctedSilicaFumeMassRatio,
      ),
    },
    material_masses: {
      binder: jsRound(binderMass, 2),
      cement: jsRound(cementMass, 2),
      fly_ash: jsRound(flyAshMass, 2),
      micro_bead: jsRound(microBeadMass, 2),
      silica_fume: jsRound(silicaFumeMass, 2),
      sand: jsRound(sandMass, 2),
      steel_fiber: jsRound(steelFiberMass, 2),
      water: jsRound(waterMass, 2),
      admixture: jsRound(admixtureMass, 2),
      total: jsRound(totalMass, 2),
    },
  }
}
