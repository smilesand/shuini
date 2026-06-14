import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { getRecordData, getRecordObject } from '../api/records'
import { getHpcWorkabilityReference, type HpcWorkabilityReferenceCode } from '../utils/hpcWorkability'
import {
  calcWaterBinder as apiCalcWaterBinder,
  fitCoefficients as apiFitCoefficients,
  calcAggregate   as apiCalcAggregate,
  calcBinder      as apiCalcBinder,
  calcWaterAdmixture as apiCalcWaterAdmixture,
} from '../api/calc'

export const useCalcStore = defineStore('calc', () => {
  // ── Generic ─────────────────────────────────────────────────────────────
  const loading = ref(false) // 当前计算请求状态
  const error   = ref<string | null>(null) // 当前错误信息
  const currentRecordId = ref<number | null>(null) // 当前配比记录 ID
  const currentRecordName = ref('') // 当前配比名称
  const currentRecordProjectId = ref<number | null>(null) // 当前配比所属项目 ID
  const currentTrialData = ref<object | null>(null) // 当前记录已保存的试配快照
  const hpcSelectedProjectId = ref<number | null>(null) // 高性能混凝土当前选中项目 ID
  const hpcShowCalculator = ref(false) // 高性能混凝土页是否显示计算卡片

  // ── Tab 1: 水胶比 ─────────────────────────────────────────────────────
  const fcuk = ref<number | null>(null) // 强度等级 fcu,k
  const fb   = ref<number | null>(null) // 胶材 28d 强度 fb
  const fbCalcMode = ref<'input' | 'calc'>('input') // fb 输入模式
  const fceG = ref<number>(42.5) // 水泥强度等级 fce,g
  const gammaC = ref<number>(1.10) // 水泥富余系数 γc
  const gammaF = ref<number>(1.00) // 粉煤灰影响系数 γf
  const gammaS = ref<number>(1.00) // 矿粉影响系数 γs
  const gammaB = ref<number>(1.00) // 微珠影响系数 γb
  const gammaSF = ref<number>(1.00) // 硅灰影响系数 γSF

  const aa   = ref(0.33) // 回归系数 αa
  const ab   = ref(1.09) // 回归系数 αb
  const ac   = ref(-49.54) // 回归系数 αc
  const fcu0 = ref<number | null>(null) // 配制强度 fcu,0
  const wb   = ref<number | null>(null) // 水胶比 W/B

  // fcuk 变化时自动计算 fcu0（不依赖 fb）
  watch(fcuk, (val) => {
    fcu0.value = val !== null ? parseFloat((val * 1.15).toFixed(2)) : null
  })

  // ── Tab 2: 砂率 ──────────────────────────────────────────────────────
  const sandRatioRow       = ref<number | null>(null) // 砂率参考表选中强度行
  const sandRatioCol       = ref<number | null>(null) // 砂率参考表选中粒径列
  const sandRatioInput     = ref<number | null>(null) // 砂率 βs
  const sandRatioConfirmed = ref(false) // 砂率已确认
  const vgReferenceCode    = ref<HpcWorkabilityReferenceCode | null>(null) // Vg 参考范围选中工作性等级

  // ── Tab 3: 骨料用量 ───────────────────────────────────────────────────
  const vg   = ref<number | null>(null) // 粗骨料绝对体积 Vg
  const rhog = ref<number | null>(null) // 粗骨料密度 ρg
  const rhos = ref<number | null>(null) // 细骨料密度 ρs
  const mg   = ref<number | null>(null) // 粗骨料用量 mg
  const ms   = ref<number | null>(null) // 细骨料用量 ms

  // ── Tab 4: 胶凝材料 ───────────────────────────────────────────────────
  const b1p  = ref<number | null>(null) // 粉煤灰掺量 β1
  const rho1 = ref<number | null>(null) // 粉煤灰密度 ρ1
  const b2p  = ref<number | null>(null) // 矿粉掺量 β2
  const rho2 = ref<number | null>(null) // 矿粉密度 ρ2
  const b3p  = ref<number | null>(null) // 微珠掺量 β3
  const rho3 = ref<number | null>(null) // 微珠密度 ρ3
  const b4p  = ref<number | null>(null) // 硅灰掺量 β4
  const rho4 = ref<number | null>(null) // 硅灰密度 ρ4
  const rhoc = ref<number | null>(null) // 水泥密度 ρc
  const va   = ref<number | null>(null) // 含气量 Va
  const bc   = ref<number | null>(null) // 水泥比 βc
  const rhob = ref<number | null>(null) // 胶材密度 ρb
  const vp   = ref<number | null>(null) // 浆体体积 Vp
  const mb   = ref<number | null>(null) // 胶凝材料总量 mb
  const m1   = ref<number | null>(null) // 粉煤灰用量 m1
  const m2   = ref<number | null>(null) // 矿粉用量 m2
  const m3   = ref<number | null>(null) // 微珠用量 m3
  const m4   = ref<number | null>(null) // 硅灰用量 m4
  const mc   = ref<number | null>(null) // 水泥用量 mc

  // ── Tab 5: 水和外加剂 ─────────────────────────────────────────────────
  const alpha = ref<number | null>(null) // 外加剂掺量 α
  const mw    = ref<number | null>(null) // 用水量 mw
  const ma    = ref<number | null>(null) // 外加剂用量 ma

  // ── Getters ───────────────────────────────────────────────────────────
  const totalMass = computed<number | null>(() => {
    const vals = [mb.value, mg.value, ms.value, mw.value, ma.value]
    if (vals.some(v => v === null)) return null
    return vals.reduce((a, b) => (a as number) + (b as number), 0) as number
  }) // 每立方混凝土材料合计

  const sandRatio = computed<number | null>(() =>
    sandRatioConfirmed.value ? sandRatioInput.value : null
  ) // 已确认的砂率 βs

  function setCurrentRecord(recordId: number | null, name = '', projectId: number | null = null) {
    currentRecordId.value = recordId
    currentRecordName.value = name
    currentRecordProjectId.value = projectId
  }

  function markRecordSaved(recordId: number, name: string, projectId: number | null = null) {
    setCurrentRecord(recordId, name, projectId)
  }

  function setCurrentTrialData(trialData: object | null) {
    currentTrialData.value = trialData
  }

  function setHpcProjectState(projectId: number | null, showCalculatorVisible = hpcShowCalculator.value) {
    hpcSelectedProjectId.value = projectId
    hpcShowCalculator.value = showCalculatorVisible
  }

  function clearHpcProjectState() {
    setHpcProjectState(null, false)
  }

  function applyRecordData(record: Record<string, unknown>) {
    resetAll()

    const recordId = typeof record.id === 'number' ? record.id : null
    const recordName = typeof record.name === 'string' ? record.name : ''
    const recordProjectId = typeof record.project_id === 'number' ? record.project_id : null
    const recordData = getRecordData(record)
    const recordTrialData = getRecordObject(record, 'trial_data')
    setCurrentRecord(recordId, recordName, recordProjectId)
    setCurrentTrialData(
      recordTrialData && typeof recordTrialData === 'object' && !Array.isArray(recordTrialData)
        ? recordTrialData
        : null,
    )

    if (recordData.fcuk != null) fcuk.value = Number(recordData.fcuk)
    if (recordData.fb != null) fb.value = Number(recordData.fb)
    if (recordData.fcu0 != null) fcu0.value = Number(recordData.fcu0)
    if (recordData.wb != null) wb.value = Number(recordData.wb)
    if (recordData.fbCalcMode != null) fbCalcMode.value = String(recordData.fbCalcMode) as 'input' | 'calc'
    if (recordData.fceG != null) fceG.value = Number(recordData.fceG)
    if (recordData.gammaC != null) gammaC.value = Number(recordData.gammaC)
    if (recordData.gammaF != null) gammaF.value = Number(recordData.gammaF)
    if (recordData.gammaS != null) gammaS.value = Number(recordData.gammaS)
    if (recordData.gammaB != null) gammaB.value = Number(recordData.gammaB)
    if (recordData.gammaSF != null) gammaSF.value = Number(recordData.gammaSF)
    if (recordData.aa != null) aa.value = Number(recordData.aa)
    if (recordData.ab != null) ab.value = Number(recordData.ab)
    if (recordData.ac != null) ac.value = Number(recordData.ac)
    if (recordData.sand_ratio != null) {
      sandRatioInput.value = Number(recordData.sand_ratio)
      confirmSandRatio()
    }
    if (typeof recordData.vg_reference_code === 'string') {
      vgReferenceCode.value = getHpcWorkabilityReference(recordData.vg_reference_code)?.code ?? null
    }
    if (recordData.vg != null) vg.value = Number(recordData.vg)
    if (recordData.rhog != null) rhog.value = Number(recordData.rhog)
    if (recordData.rhos != null) rhos.value = Number(recordData.rhos)
    if (recordData.mg != null) mg.value = Number(recordData.mg)
    if (recordData.ms != null) ms.value = Number(recordData.ms)
    if (recordData.b1p != null) b1p.value = Number(recordData.b1p)
    if (recordData.rho1 != null) rho1.value = Number(recordData.rho1)
    if (recordData.b2p != null) b2p.value = Number(recordData.b2p)
    if (recordData.rho2 != null) rho2.value = Number(recordData.rho2)
    if (recordData.b3p != null) b3p.value = Number(recordData.b3p)
    if (recordData.rho3 != null) rho3.value = Number(recordData.rho3)
    if (recordData.b4p != null) b4p.value = Number(recordData.b4p)
    if (recordData.rho4 != null) rho4.value = Number(recordData.rho4)
    if (recordData.rhoc != null) rhoc.value = Number(recordData.rhoc)
    if (recordData.va != null) va.value = Number(recordData.va)
    if (recordData.bc != null) bc.value = Number(recordData.bc)
    if (recordData.rhob != null) rhob.value = Number(recordData.rhob)
    if (recordData.vp != null) vp.value = Number(recordData.vp)
    if (recordData.mb != null) mb.value = Number(recordData.mb)
    if (recordData.m1 != null) m1.value = Number(recordData.m1)
    if (recordData.m2 != null) m2.value = Number(recordData.m2)
    if (recordData.m3 != null) m3.value = Number(recordData.m3)
    if (recordData.m4 != null) m4.value = Number(recordData.m4)
    if (recordData.mc != null) mc.value = Number(recordData.mc)
    if (recordData.alpha != null) alpha.value = Number(recordData.alpha)
    if (recordData.mw != null) mw.value = Number(recordData.mw)
    if (recordData.ma != null) ma.value = Number(recordData.ma)
  }

  function buildRecordPayload(
    category: 'hpc' | 'uhpc',
    name: string,
    projectId: number | null = null,
    recordId: number | null = currentRecordId.value,
  ) {
    return {
      ...(recordId !== null ? { id: recordId } : {}),
      name,
      category,
      project_id: projectId,
      record_data: {
        fcuk: fcuk.value,
        fb: fb.value,
        fbCalcMode: fbCalcMode.value,
        fceG: fceG.value,
        gammaC: gammaC.value,
        gammaF: gammaF.value,
        gammaS: gammaS.value,
        gammaB: gammaB.value,
        gammaSF: gammaSF.value,
        fcu0: fcu0.value,
        wb: wb.value,
        aa: aa.value,
        ab: ab.value,
        ac: ac.value,
        sand_ratio: sandRatioConfirmed.value ? sandRatioInput.value : null,
        vg_reference_code: vgReferenceCode.value,
        vg: vg.value,
        rhog: rhog.value,
        rhos: rhos.value,
        mg: mg.value,
        ms: ms.value,
        b1p: b1p.value,
        rho1: rho1.value,
        b2p: b2p.value,
        rho2: rho2.value,
        b3p: b3p.value,
        rho3: rho3.value,
        b4p: b4p.value,
        rho4: rho4.value,
        rhoc: rhoc.value,
        va: va.value,
        bc: bc.value,
        rhob: rhob.value,
        vp: vp.value,
        mb: mb.value,
        m1: m1.value,
        m2: m2.value,
        m3: m3.value,
        m4: m4.value,
        mc: mc.value,
        alpha: alpha.value,
        mw: mw.value,
        ma: ma.value,
        total_mass: totalMass.value,
      },
    }
  }

  // ── Actions ───────────────────────────────────────────────────────────
  async function calcWaterBinder() {
    if (fcuk.value === null || fb.value === null) return
    loading.value = true; error.value = null
    try {
      const res = await apiCalcWaterBinder({
        fcuk: fcuk.value, fb: fb.value,
        aa: aa.value, ab: ab.value, ac: ac.value,
      })
      fcu0.value = res.fcu0
      wb.value   = res.wb
    } catch (e: unknown) {
      error.value = (e instanceof Error) ? e.message : '计算失败'
    } finally {
      loading.value = false
    }
  }

  async function fitCoefficients(csvText: string) {
    loading.value = true; error.value = null
    try {
      const res = await apiFitCoefficients({ csv_text: csvText })
      aa.value = res.aa
      ab.value = res.ab
      ac.value = res.ac
      await calcWaterBinder()
    } catch (e: unknown) {
      error.value = (e instanceof Error) ? e.message : '拟合失败'
    } finally {
      loading.value = false
    }
  }

  function confirmSandRatio() {
    if (sandRatioInput.value !== null && sandRatioInput.value > 0) {
      sandRatioConfirmed.value = true
    }
  }

  async function calcAggregate() {
    if (!vg.value || !rhog.value || !sandRatioConfirmed.value || !rhos.value || !sandRatioInput.value) return
    loading.value = true; error.value = null
    try {
      const res = await apiCalcAggregate({
        vg: vg.value, rhog: rhog.value,
        beta_s: sandRatioInput.value / 100,
        rhos: rhos.value,
      })
      mg.value = res.mg
      ms.value = res.ms
    } catch (e: unknown) {
      error.value = (e instanceof Error) ? e.message : '计算失败'
    } finally {
      loading.value = false
    }
  }

  async function calcBinder() {
    if (!rhoc.value || !wb.value || !mg.value || !ms.value || !rhog.value || !rhos.value) return
    loading.value = true; error.value = null
    try {
      const res = await apiCalcBinder({
        b1p: b1p.value ?? 0, rho1: rho1.value ?? 2200,
        b2p: b2p.value ?? 0, rho2: rho2.value ?? 2900,
        b3p: b3p.value ?? 0, rho3: rho3.value ?? 2600,
        b4p: b4p.value ?? 0, rho4: rho4.value ?? 2200,
        rhoc: rhoc.value, va: va.value ?? 0.01,
        mg: mg.value, ms: ms.value,
        rhog: rhog.value, rhos: rhos.value,
        wb: wb.value,
      })
      bc.value   = res.bc
      rhob.value = res.rhob
      vp.value   = res.vp
      mb.value   = res.mb
      m1.value = res.m1; m2.value = res.m2
      m3.value = res.m3; m4.value = res.m4; mc.value = res.mc
    } catch (e: unknown) {
      error.value = (e instanceof Error) ? e.message : '计算失败'
    } finally {
      loading.value = false
    }
  }

  async function calcWaterAdmixture() {
    if (!alpha.value || !mb.value || !wb.value) return
    loading.value = true; error.value = null
    try {
      const res = await apiCalcWaterAdmixture({
        mb: mb.value, wb: wb.value, alpha: alpha.value,
      })
      mw.value = res.mw
      ma.value = res.ma
    } catch (e: unknown) {
      error.value = (e instanceof Error) ? e.message : '计算失败'
    } finally {
      loading.value = false
    }
  }

  function resetAll() {
    loading.value = false; error.value = null
    setCurrentRecord(null)
    setCurrentTrialData(null)
    fcuk.value = null; fb.value = null
    fbCalcMode.value = 'input'
    fceG.value = 42.5; gammaC.value = 1.10
    gammaF.value = 1.0; gammaS.value = 1.0; gammaB.value = 1.0; gammaSF.value = 1.0
    aa.value = 0.33; ab.value = 1.09; ac.value = -49.54
    fcu0.value = null; wb.value = null
    sandRatioRow.value = null; sandRatioCol.value = null
    sandRatioInput.value = null; sandRatioConfirmed.value = false
    vgReferenceCode.value = null
    vg.value = null; rhog.value = null; rhos.value = null
    mg.value = null; ms.value = null
    b1p.value = null; b2p.value = null; b3p.value = null; b4p.value = null
    rho1.value = null; rho2.value = null; rho3.value = null; rho4.value = null
    rhoc.value = null; va.value = null
    bc.value = null; rhob.value = null; vp.value = null; mb.value = null
    m1.value = null; m2.value = null; m3.value = null; m4.value = null; mc.value = null
    alpha.value = null; mw.value = null; ma.value = null
  }

  return {
    loading, error,
    currentRecordId, currentRecordName, currentRecordProjectId,
    currentTrialData,
    hpcSelectedProjectId, hpcShowCalculator,
    fcuk, fb, fbCalcMode, fceG, gammaC, gammaF, gammaS, gammaB, gammaSF, aa, ab, ac, fcu0, wb,
    sandRatioRow, sandRatioCol, sandRatioInput, sandRatioConfirmed, vgReferenceCode,
    vg, rhog, rhos, mg, ms,
    b1p, rho1, b2p, rho2, b3p, rho3, b4p, rho4,
    rhoc, va, bc, rhob, vp, mb, m1, m2, m3, m4, mc,
    alpha, mw, ma,
    totalMass, sandRatio,
    setCurrentRecord,
    markRecordSaved,
    setCurrentTrialData,
    setHpcProjectState,
    clearHpcProjectState,
    applyRecordData,
    buildRecordPayload,
    calcWaterBinder,
    fitCoefficients,
    confirmSandRatio,
    calcAggregate,
    calcBinder,
    calcWaterAdmixture,
    resetAll,
  }
})
