// 说明：所有混凝土配比计算已迁移到前端集中式引擎（src/calc）。
// 服务端仅负责数据持久化，因此此文件只保留供引擎复用的请求/响应类型定义，不再发起计算接口请求。

// ── Request / Response Types ────────────────────────────────────────────────

export interface WaterBinderReq {
  fcuk: number
  fb: number
  aa?: number
  ab?: number
  ac?: number
}
export interface WaterBinderRes {
  fcu0: number
  wb: number
}

export interface FitCoefficientsReq {
  csv_text: string
}
export interface FitCoefficientsRes {
  aa: number
  ab: number
  ac: number
  r2: number
}

export interface AggregateReq {
  vg: number
  rhog: number
  beta_s: number
  rhos: number
}
export interface AggregateRes {
  mg: number
  ms: number
}

export interface BinderReq {
  b1p: number; rho1: number
  b2p: number; rho2: number
  b3p: number; rho3: number
  b4p: number; rho4: number
  rhoc: number
  va: number
  mg: number; ms: number
  rhog: number; rhos: number
  wb: number
}
export interface BinderRes {
  bc: number
  rhob: number
  vp: number
  mb: number
  m1: number; m2: number; m3: number; m4: number; mc: number
}

export interface WaterAdmixtureReq {
  mb: number
  wb: number
  alpha: number
}
export interface WaterAdmixtureRes {
  mw: number
  ma: number
}

export interface UhpcMixReq {
  strength_grade: number
  water_binder_ratio: number
  admixture_ratio: number
  sand_binder_ratio: number
  steel_fiber_volume_ratio: number
  max_particle_size: number
  min_particle_size: number
  distribution_index: number
  fly_ash_peak_size: number
  fly_ash_accumulation_size: number
  micro_bead_peak_size: number
  micro_bead_silica_fume_ratio: number
  cement_density: number
  fly_ash_density: number
  micro_bead_density: number
  silica_fume_density: number
  micro_powder_coefficient: number
  assumed_mix_mass: number
  steel_fiber_density: number
}

export interface UhpcRatioRes {
  cement: number
  fly_ash: number
  micro_bead: number
  silica_fume: number
}

export interface UhpcMassRatioSetRes {
  initial: UhpcRatioRes
  corrected: UhpcRatioRes
}

export interface UhpcMaterialMassesRes {
  binder: number
  cement: number
  fly_ash: number
  micro_bead: number
  silica_fume: number
  sand: number
  steel_fiber: number
  water: number
  admixture: number
  total: number
}

export interface UhpcMixRes {
  design_strength: number
  assumed_mix_mass: number
  steel_fiber_density: number
  binder_volume_ratios: UhpcRatioRes
  binder_mass_ratios: UhpcMassRatioSetRes
  material_masses: UhpcMaterialMassesRes
}

// ── HPC Trial Request / Response Types ─────────────────────────────────────

/**
 * 高性能试配统一计算请求。
 *
 * 前端把主计算页得到的基准配合比和试配页当前输入整体交给后端，
 * 所有派生结果都由服务端统一返回，避免前端继续保留业务公式。
 */
export interface HpcTrialReq {
  wb: number
  beta_s: number
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
  alpha: number
  batch_volume: number
  workability_binder_delta: number
  workability_sand_ratio_delta: number
  workability_alpha_delta: number
  delta_wb: number
  delta_bs: number
  strength0: number | null
  strength_p: number | null
  strength_n: number | null
  target_strength: number | null
  wb_adj: number | null
  mb_adj: number | null
  sand_ratio_adj: number | null
  alpha_adj: number | null
  measured_density: number | null
  trial_alpha?: number | null
  trial_ma0?: number | null
  trial_maP?: number | null
  trial_maN?: number | null
}

export interface HpcTrialMaterialRowRes {
  key: string
  label: string
  trial_val: number | null
}

export interface HpcTrialMaterialResultRes {
  mc: number | null
  m1: number | null
  m2: number | null
  m3: number | null
  m4: number | null
  mg: number | null
  ms: number | null
  mw: number | null
  ma: number | null
  total: number | null
}

export interface HpcTrialWorkabilityResultRes extends HpcTrialMaterialResultRes {
  mb: number | null
  wb: number | null
  bs: number | null
  alpha: number | null
}

export interface HpcTrialStrengthMixRes extends HpcTrialMaterialResultRes {
  label: string
  wb: number | null
  bs: number | null
  mb: number | null
}

export interface HpcTrialStrengthRegressionRes {
  a: number
  b: number
  r2: number
  recommend_wb: number | null
  predict_strength: number | null
}

export interface HpcTrialChartDataRes {
  min_bw: number
  max_bw: number
  range_bw: number
  min_strength: number
  max_strength: number
  range_strength: number
  bw_ratios: number[]
  strengths: number[]
}

export interface HpcTrialRes {
  base_wb: number
  base_bs: number
  base_alpha: number
  workability_result: HpcTrialWorkabilityResultRes
  trial_materials: HpcTrialMaterialRowRes[]
  strength_mixes: HpcTrialStrengthMixRes[]
  strength_regression: HpcTrialStrengthRegressionRes | null
  chart_data: HpcTrialChartDataRes | null
  adapt_result: HpcTrialMaterialResultRes
  calculated_density: number | null
  density_correction_factor: number | null
  lab_mix: HpcTrialMaterialResultRes
}

// ── UHPC Trial ─────────────────────────────────────────────────────────────

export interface UhpcTrialReq {
  wb: number
  sb: number
  alpha: number
  sf_mass: number
  total: number
  cement_pct: number
  fly_ash_pct: number
  micro_bead_pct: number
  silica_fume_pct: number
  design_strength: number
  adjusted_sb: number | null
  adjusted_alpha: number | null
  s_wb_0: number | null
  s_wb_plus: number | null
  s_wb_minus: number | null
  s_sf_plus: number | null
  s_sf_minus: number | null
  a_wb_plus: number | null
  a_wb_minus: number | null
  a_sf_plus: number | null
  a_sf_minus: number | null
  corr_base: 'trial' | 'wbRec' | 'sfRec'
  measured_density: number | null
}

export interface UhpcTrialMixRowRes {
  cement: number
  fly_ash: number
  micro_bead: number
  silica_fume: number
  sand: number
  steel_fiber: number
  water: number
  admixture: number
  admixture_pct?: number
  binder: number
  total: number
}

export interface UhpcTrialRes {
  design_strength: number
  trial_sb: number
  trial_alpha: number
  trial_mix: UhpcTrialMixRowRes
  variant_wb_plus: UhpcTrialMixRowRes
  variant_wb_minus: UhpcTrialMixRowRes
  variant_sf_plus: UhpcTrialMixRowRes
  variant_sf_minus: UhpcTrialMixRowRes
  rec_wb: number | null
  rec_sf: number | null
  corr_base: string
  corr_mix: UhpcTrialMixRowRes
  calc_density: number | null
  corr_factor: number | null
  needs_corr: boolean
  lab_mix: UhpcTrialMixRowRes
}

// ── Adapt ──────────────────────────────────────────────────────────────────

export interface AdaptReq {
  mb_adj: number
  beta_s_adj: number   // 小数 (0~1)
  alpha_adj: number    // 百分比 (%)
  wb: number
  bc: number           // 水泥质量分数（小数）
  b1: number; b2: number; b3: number; b4: number
  mg: number
}
export interface AdaptRes {
  mb: number; mc: number
  m1: number; m2: number; m3: number; m4: number
  mg: number; ms: number; mw: number; ma: number
}
