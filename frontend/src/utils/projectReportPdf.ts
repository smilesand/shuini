import type { Project } from '../api/projects'
import type { RecordItem } from '../api/records'
import { computeGroupValue } from '../composables/useStrengthEval'
import { generateReportHtml } from './reportHtml'
import html2pdf from 'html2pdf.js'

function categoryLabel(cat: string) {
  if (cat === 'uhpc') return 'UHPC'
  if (cat === 'hpc') return 'HPC'
  if (cat === 'hpc_trial') return 'HPC试配'
  if (cat === 'uhpc_trial') return 'UHPC试配'
  return cat
}

function categoryOrder(cat: string) {
  const order: Record<string, number> = { hpc: 1, hpc_trial: 2, uhpc: 3, uhpc_trial: 4 }
  return order[cat] ?? 99
}

function fmtDate(value: string) {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

function extractEval(record: RecordItem, key: string) {
  const trialData = record.record_data?.trial_data as any
  if (!trialData) return ''
  const val = trialData.inputs ? trialData.inputs[key] : trialData[key]
  if (val === null || val === undefined) return ''
  return val
}

function pickObject(...candidates: unknown[]): Record<string, unknown> | null {
  for (const candidate of candidates) {
    if (candidate && typeof candidate === 'object' && !Array.isArray(candidate)) {
      return candidate as Record<string, unknown>
    }
  }
  return null
}

function resolveFinalMix(record: RecordItem, flatData: Record<string, unknown>): Record<string, unknown> {
  const recordData = record.record_data as Record<string, unknown> | undefined
  const trialData = recordData?.trial_data as Record<string, unknown> | undefined
  const trialCalc = trialData?.calculated as Record<string, unknown> | undefined
  const calc = recordData?.calculated as Record<string, unknown> | undefined
  return pickObject(
    trialCalc?.labMix,
    trialCalc?.lab_mix,
    trialData?.lab_mix,
    trialCalc?.adaptResult,
    trialCalc?.adapt_result,
    calc?.labMix,
    calc?.lab_mix,
    calc?.adaptResult,
    calc?.adapt_result,
    calc?.mixProportion,
    calc,
    flatData,
  ) ?? flatData
}

function flattenData(data: unknown): Record<string, any> {
  const flatData: Record<string, any> = {}
  function flattenObj(obj: any) {
    if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return
    for (const [key, value] of Object.entries(obj)) {
      if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
        flattenObj(value)
      } else {
        flatData[key] = value
      }
    }
  }
  flattenObj(data)
  return flatData
}

function buildRecordReportHtml(project: Project | null, record: RecordItem): string {
  const data = record.record_data ?? {}

  const rawGroups = extractEval(record, 'strengthGroups')
  let strengthGroups: { id: string; values: (number | null)[] }[] = []
  if (Array.isArray(rawGroups)) {
    strengthGroups = (rawGroups as any[]).map((group: any) => ({
      id: String(group.id ?? ''),
      values: Array.isArray(group.values) ? group.values.slice(0, 3) : [null, null, null],
    }))
  }
  if (strengthGroups.length === 0) {
    const legacy = extractEval(record, 'evalStrength28d')
    if (legacy) {
      const vals: (number | null)[] = [Number(legacy) || null, null, null]
      strengthGroups = [
        { id: 'G01', values: vals },
        { id: 'G02', values: [null, null, null] },
        { id: 'G03', values: [null, null, null] },
        { id: 'G04', values: [null, null, null] },
        { id: 'G05', values: [null, null, null] },
        { id: 'G06', values: [null, null, null] },
      ]
    }
  }

  const groupEvals = strengthGroups.map(group => computeGroupValue(group.values))
  const validGroupAvgs = groupEvals.filter(item => !item.invalid).map(item => item.value).filter((value): value is number => value !== null)
  const strengthOverallAvg = validGroupAvgs.length > 0 ? validGroupAvgs.reduce((sum, value) => sum + value, 0) / validGroupAvgs.length : null
  const strengthMinGroupAvg = validGroupAvgs.length > 0 ? Math.min(...validGroupAvgs) : null

  const evalSlump = extractEval(record, 'evalSlump') || extractEval(record, 'slumpMeasured')
  const evalSpread = extractEval(record, 'evalSpread') || extractEval(record, 'spreadMeasured')
  const workDesc = extractEval(record, 'evalWorkabilityDesc') || extractEval(record, 'workabilityNote')
  const workabilityOk = extractEval(record, 'workabilityOk')
  const sTargetStr = extractEval(record, 'sTargetStrength')

  let strengthPass: boolean | null = null
  let workabilityPass: boolean | null = null
  if (workabilityOk === true || workabilityOk === 'true' || workabilityOk === 1 || workabilityOk === '1') {
    workabilityPass = true
  } else if (workabilityOk === false || workabilityOk === 'false' || workabilityOk === 0 || workabilityOk === '0') {
    workabilityPass = false
  }

  const flatData = flattenData(data)
  const isUHPC = record.category === 'uhpc' || record.category === 'uhpc_trial'
  const strengthGrade = flatData.strengthGrade || flatData.strength_grade || flatData.fcuk || '—'
  const designStrength = flatData.fcu0 || flatData.designStrength || flatData.design_strength || flatData.sTargetStrength || '—'
  const totalBinder = flatData.mb || flatData.total_binder || (flatData.binder && typeof flatData.binder === 'number' ? flatData.binder : null) || '—'
  const cementPct = flatData.bcp || flatData.bc || flatData.cement || flatData.cement_pct || flatData.cementRatio || '—'
  const p1 = flatData.b1p ?? flatData.flyAsh ?? flatData.fly_ash_pct ?? '—'
  const p2 = flatData.b2p ?? flatData.slagPowder ?? flatData.slag_powder_pct ?? '—'
  const p3 = flatData.b3p ?? flatData.microBead ?? flatData.micro_bead_pct ?? '—'
  const p4 = flatData.b4p ?? flatData.silicaFume ?? flatData.silica_fume_pct ?? '—'
  let wb = flatData.wbAdj ?? flatData.recWb ?? flatData.recommend_wb ?? flatData.recommendWb ?? flatData.wb ?? flatData.waterBinderRatio ?? flatData.water_binder_ratio ?? '—'
  let sandR = flatData.sandRatioAdj ?? flatData.beta_s ?? flatData.sandRatio ?? flatData.sand_ratio ?? '—'
  if (typeof sandR === 'number' && sandR < 1) sandR = sandR * 100
  let sb = flatData.sb ?? flatData.sandBinderRatio ?? flatData.sand_binder_ratio ?? '—'
  let admix = flatData.alphaAdj ?? flatData.alpha ?? flatData.admixtureRatio ?? flatData.admixture_ratio ?? flatData.admixture_pct ?? '—'
  if (typeof admix === 'number' && flatData.admixtureRatio === undefined && flatData.admixture_ratio === undefined && flatData.admixture_pct === undefined && admix < 1) admix = admix * 100
  const sf_vol = flatData.steelFiberVolumeRatio ?? flatData.steel_fiber_volume_ratio ?? flatData.steelFiberVolume ?? '—'
  const vgReferenceCode = (flatData.vg_reference_code as string) ?? null

  const reqSlump = flatData.req_slump ?? flatData.reqSlump ?? null
  const reqSpread = flatData.req_spread ?? flatData.reqSpread ?? null
  const maxAggregateSize = (flatData.max_aggregate_size ?? flatData.maxAggregateSize ?? null) as string | null
  const fb = flatData.fb ?? flatData.binderStrength28d ?? null
  const rhoc = flatData.rhoc ?? null
  const rho1 = flatData.rho1 ?? null
  const rho2 = flatData.rho2 ?? null
  const rho3 = flatData.rho3 ?? null
  const rho4 = flatData.rho4 ?? null
  const rhog = flatData.rhog ?? null
  const rhos = flatData.rhos ?? null
  const tensileStrength = flatData.tensile_strength ?? flatData.tensileStrength ?? null
  const maxParticleSize = flatData.max_particle_size ?? flatData.maxParticleSize ?? null
  const flyAshPeakSize = flatData.fly_ash_peak_size ?? flatData.flyAshPeakSize ?? null
  const microBeadPeakSize = flatData.micro_bead_peak_size ?? flatData.microBeadPeakSize ?? null
  const airContent = flatData.air_content ?? flatData.va ?? null
  const vg = flatData.vg ?? null

  const targetForEval = sTargetStr || flatData.fcu0 || flatData.designStrength || flatData.design_strength
  const strengthGradeNum = Number(flatData.fcuk || flatData.strengthGrade || flatData.strength_grade || NaN)
  if (strengthOverallAvg !== null && Number.isFinite(strengthGradeNum)) {
    const strengthMult = isUHPC ? 1.10 : 1.15
    const overallOk = strengthOverallAvg >= strengthGradeNum * strengthMult
    const minThreshold = strengthGradeNum * 0.95
    const minGroupOk = strengthMinGroupAvg !== null ? strengthMinGroupAvg >= minThreshold : null
    strengthPass = overallOk && (minGroupOk !== false)
  }

  const mix = resolveFinalMix(record, flatData)
  const mmc = mix.mc ?? mix.cement ?? '—'
  const mm1 = mix.m1 ?? mix.flyAsh ?? mix.fly_ash ?? '—'
  const mm2 = mix.m2 ?? mix.slagPowder ?? mix.slag_powder ?? '—'
  const mm3 = mix.m3 ?? mix.microBead ?? mix.micro_bead ?? '—'
  const mm4 = mix.m4 ?? mix.silicaFume ?? mix.silica_fume ?? '—'
  const mmg = mix.mg ?? mix.coarseAgg ?? mix.coarse_agg ?? '—'
  const mms = mix.ms ?? mix.sand ?? '—'
  const mmw = mix.mw ?? mix.water ?? '—'
  const mma = mix.ma ?? mix.admixture ?? mix.admixture_mass ?? '—'
  const msf = mix.msf ?? mix.steelFiber ?? mix.steel_fiber ?? mix.steelFiberMass ?? '—'
  const mtot = mix.total ?? mix.totalMass ?? mix.total_mass ?? '—'

  const vBatch = Number(flatData.batchVolume ?? flatData.batch_volume ?? 20)
  const vScale = vBatch / 1000
  const toNum = (value: unknown) => (typeof value === 'number' ? value : NaN)
  const bmc = mmc !== '—' ? (toNum(mmc) * vScale) : '—'
  const bm1 = mm1 !== '—' ? (toNum(mm1) * vScale) : '—'
  const bm2 = mm2 !== '—' ? (toNum(mm2) * vScale) : '—'
  const bm3 = mm3 !== '—' ? (toNum(mm3) * vScale) : '—'
  const bm4 = mm4 !== '—' ? (toNum(mm4) * vScale) : '—'
  const bmg = mmg !== '—' ? (toNum(mmg) * vScale) : '—'
  const bms = mms !== '—' ? (toNum(mms) * vScale) : '—'
  const bmw = mmw !== '—' ? (toNum(mmw) * vScale) : '—'
  const bma = mma !== '—' ? (toNum(mma) * vScale) : '—'
  const bmsf = msf !== '—' ? (toNum(msf) * vScale) : '—'
  const bmtot = mtot !== '—' ? (toNum(mtot) * vScale) : '—'

  return generateReportHtml({
    project,
    record,
    categoryLabel: categoryLabel(record.category),
    fmtDate: fmtDate(record.created_at),
    strengthGrade: String(strengthGrade),
    designStrength,
    totalBinder,
    cementPct,
    p1, p2, p3, p4,
    wb, sandR, sb, admix, sf_vol,
    isUHPC,
    mmc, mm1, mm2, mm3, mm4, mmg, mms, mmw, mma, msf, mtot,
    bmc, bm1, bm2, bm3, bm4, bmg, bms, bmw, bma, bmsf, bmtot,
    vBatch,
    evalSlump, evalSpread, workDesc,
    workabilityPass,
    strengthPass,
    vgReferenceCode,
    reqSlump, reqSpread, maxAggregateSize,
    fb, rhoc, rho1, rho2, rho3, rho4, rhog, rhos,
    tensileStrength, maxParticleSize, flyAshPeakSize, microBeadPeakSize, vg, airContent,
    strengthGroups,
    groupEvals,
    strengthOverallAvg,
    strengthMinGroupAvg,
    strengthGradeNum,
    targetForEval,
  })
}

function extractHtmlPart(html: string, selector: 'style' | 'page'): string {
  const doc = new DOMParser().parseFromString(html, 'text/html')
  if (selector === 'style') return doc.querySelector('style')?.innerHTML ?? ''
  return doc.querySelector('.page-container')?.outerHTML ?? ''
}

export function buildProjectReportHtml(project: Project, records: RecordItem[]): string {
  const sortedRecords = [...records].sort((a, b) => {
    const categoryDiff = categoryOrder(a.category) - categoryOrder(b.category)
    if (categoryDiff !== 0) return categoryDiff
    return String(a.name).localeCompare(String(b.name), 'zh-CN')
  })

  const recordHtmlList = sortedRecords.map(record => buildRecordReportHtml(project, record))
  const baseStyle = extractHtmlPart(recordHtmlList[0] ?? '', 'style')
  const pages = recordHtmlList.map(html => `<section class="project-pdf-page">${extractHtmlPart(html, 'page')}</section>`).join('')

  return `<!DOCTYPE html><html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>${project.project_name} - 项目配比记录</title>
<style>
${baseStyle}
body { background: #fff; }
.project-pdf-page {
  width: 281mm;
  break-after: page;
  display: flex;
  align-items: flex-start;
  justify-content: center;
}
.project-pdf-page:last-child {
  break-after: auto;
}
.project-pdf-page .page-container { margin: 0 auto; }
</style>
</head>
<body>${pages}</body>
</html>`
}

function sanitizeFilename(value: string) {
  return value.replace(/[\\/:*?"<>|]/g, '_').replace(/\s+/g, '_') || 'project_report'
}

export async function exportProjectReportPdf(project: Project, records: RecordItem[]) {
  const html = buildProjectReportHtml(project, records)
  const element = document.createElement('div')
  element.innerHTML = html
  try {
    await html2pdf()
      .set({
        margin: [8, 8, 8, 8],
        filename: `${sanitizeFilename(project.project_code || project.project_name)}_项目配比记录.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'landscape' },
      } as any)
      .from(element)
      .save()
  } finally {
    element.remove()
  }
}