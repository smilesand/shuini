import { type RecordItem } from '../api/records'
import { type Project } from '../api/projects'
import { computeGroupValue } from '../composables/useStrengthEval'
import { getHpcWorkabilityReference } from './hpcWorkability'

export interface ReportData {
  project: Project | null
  record: RecordItem
  categoryLabel: string
  fmtDate: string
  strengthGrade: string
  designStrength: unknown
  totalBinder: unknown
  cementPct: unknown
  p1: unknown; p2: unknown; p3: unknown; p4: unknown
  wb: unknown; sandR: unknown; sb: unknown; admix: unknown; sf_vol: unknown
  isUHPC: boolean
  mmc: unknown; mm1: unknown; mm2: unknown; mm3: unknown; mm4: unknown
  mmg: unknown; mms: unknown; mmw: unknown; mma: unknown; msf: unknown; mtot: unknown
  bmc: unknown; bm1: unknown; bm2: unknown; bm3: unknown; bm4: unknown
  bmg: unknown; bms: unknown; bmw: unknown; bma: unknown; bmsf: unknown; bmtot: unknown
  vBatch: number
  evalSlump: unknown; evalSpread: unknown; evalSpreadReq?: unknown; workDesc: unknown
  workabilityPass: boolean | null
  strengthPass: boolean | null
  vgReferenceCode: string | null
  reqSlump: unknown; reqSpread: unknown
  maxAggregateSize: string | null
  fb: unknown
  rhoc: unknown; rho1: unknown; rho2: unknown; rho3: unknown; rho4: unknown; rhog: unknown; rhos: unknown
  tensileStrength?: unknown
  maxParticleSize?: unknown
  flyAshPeakSize?: unknown
  microBeadPeakSize?: unknown
  vg?: unknown
  airContent?: unknown
  strengthGroups: { id: string; values: (number | null)[] }[]
  groupEvals: ReturnType<typeof computeGroupValue>[]
  strengthOverallAvg: number | null
  strengthMinGroupAvg: number | null
  strengthGradeNum: number
  targetForEval: unknown
}

function num(v: unknown): number | null {
  if (typeof v === 'number' && Number.isFinite(v)) return v
  if (typeof v === 'string' && v.trim() !== '' && v.trim() !== '—') {
    const parsed = Number(v)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function fmtVal(v: unknown, digits = 2): string {
  const n = num(v)
  if (n === null) return '—'
  return n.toFixed(digits).replace(/\.0+$/, '').replace(/(\.\d*[1-9])0+$/, '$1')
}

function textVal(v: unknown): string {
  if (v === null || v === undefined || v === '') return '—'
  return String(v)
}

function passLabel(pass: boolean | null): string {
  if (pass === true) return '<span class="pass">合格</span>'
  if (pass === false) return '<span class="fail">不合格</span>'
  return '—'
}

function sumValues(values: unknown[]): number | null {
  const nums = values.map(num).filter((v): v is number => v !== null)
  if (nums.length === 0) return null
  return nums.reduce((sum, value) => sum + value, 0)
}

function percent(part: unknown, total: unknown, fallback: unknown = null, digits = 1): string {
  const p = num(part)
  const t = num(total)
  if (p !== null && t !== null && t > 0) return fmtVal((p / t) * 100, digits)
  const f = num(fallback)
  if (f === null) return '—'
  return fmtVal(f > 0 && f < 1 ? f * 100 : f, digits)
}

function scaled(value: unknown, batchVolume: number): string {
  const n = num(value)
  if (n === null) return '—'
  return fmtVal(n * batchVolume / 1000, 2)
}

function hpcBinderTotal(d: ReportData): number | null {
  return sumValues([d.mmc, d.mm1, d.mm2, d.mm3, d.mm4]) ?? num(d.totalBinder)
}

function uhpcBinderTotal(d: ReportData): number | null {
  return sumValues([d.mmc, d.mm1, d.mm3, d.mm4]) ?? num(d.totalBinder)
}

function totalMass(d: ReportData, values: unknown[]): string {
  const explicit = num(d.mtot)
  if (explicit !== null) return fmtVal(explicit, 2)
  const summed = sumValues(values)
  return fmtVal(summed, 2)
}

function buildInfoSection(d: ReportData): string {
  return `
    <div class="section-title">一、 配合比信息</div>
    <table>
      <thead><tr><th>配合比名称</th><th>配合比类型</th><th>创建人</th><th>创建时间</th></tr></thead>
      <tbody><tr class="green"><td>${d.record.name}</td><td>${d.isUHPC ? 'UHPC' : 'HPC'}</td><td>${d.record.created_by}</td><td>${d.fmtDate}</td></tr></tbody>
    </table>`
}

function buildRequirementSection(d: ReportData): string {
  if (d.isUHPC) {
    return `
      <div class="section-title">二、 混凝土性能要求</div>
      <table>
        <thead><tr><th>强度等级/MPa</th><th>扩展度/mm</th><th>抗拉强度/MPa</th><th>其他</th></tr></thead>
        <tbody><tr class="green"><td>${textVal(d.strengthGrade)}</td><td>${fmtVal(d.reqSpread, 0)}</td><td>${fmtVal(d.tensileStrength, 1)}</td><td>—</td></tr></tbody>
      </table>`
  }
  return `
    <div class="section-title">二、 混凝土性能要求</div>
    <table>
      <thead><tr><th>强度等级/MPa</th><th>扩展度/mm</th><th>坍落度/mm</th><th>其他</th></tr></thead>
      <tbody><tr class="green"><td>${textVal(d.strengthGrade)}</td><td>${fmtVal(d.reqSpread, 0)}</td><td>${fmtVal(d.reqSlump, 0)}</td><td>—</td></tr></tbody>
    </table>`
}

function buildRawMaterialSection(d: ReportData): string {
  if (d.isUHPC) {
    return `
      <div class="section-title">三、 原材料性能</div>
      <table>
        <thead>
          <tr><th colspan="5">表观密度/kg/m³</th><th colspan="3">粒径/μm</th></tr>
          <tr><th>水泥</th><th>粉煤灰</th><th>微珠</th><th>硅灰</th><th>细骨料</th><th>体系最大粒径</th><th>粉煤灰峰值粒径</th><th>微珠峰值粒径</th></tr>
        </thead>
        <tbody><tr class="green"><td>${fmtVal(d.rhoc, 0)}</td><td>${fmtVal(d.rho1, 0)}</td><td>${fmtVal(d.rho3, 0)}</td><td>${fmtVal(d.rho4, 0)}</td><td>${fmtVal(d.rhos, 0)}</td><td>${fmtVal(d.maxParticleSize, 0)}</td><td>${fmtVal(d.flyAshPeakSize, 0)}</td><td>${fmtVal(d.microBeadPeakSize, 0)}</td></tr></tbody>
      </table>`
  }
  return `
    <div class="section-title">三、 原材料性能</div>
    <table>
      <thead>
        <tr><th rowspan="2">胶材28d强度/MPa</th><th colspan="7">表观密度/kg/m³</th><th rowspan="2">粗骨料最大粒径/mm</th></tr>
        <tr><th>水泥</th><th>粉煤灰</th><th>矿粉</th><th>微珠</th><th>硅灰</th><th>粗骨料</th><th>细骨料</th></tr>
      </thead>
      <tbody><tr class="green"><td>${fmtVal(d.fb, 1)}</td><td>${fmtVal(d.rhoc, 0)}</td><td>${fmtVal(d.rho1, 0)}</td><td>${fmtVal(d.rho2, 0)}</td><td>${fmtVal(d.rho3, 0)}</td><td>${fmtVal(d.rho4, 0)}</td><td>${fmtVal(d.rhog, 0)}</td><td>${fmtVal(d.rhos, 0)}</td><td>${textVal(d.maxAggregateSize)}</td></tr></tbody>
    </table>`
}

function buildKeyParamsSection(d: ReportData): string {
  if (d.isUHPC) {
    const binder = uhpcBinderTotal(d)
    const water = num(d.mmw)
    const admixtureMass = num(d.mma)
    const wb = water !== null && binder !== null && binder > 0 ? water / binder : d.wb
    const admix = admixtureMass !== null && binder !== null && binder > 0 ? (admixtureMass / binder) * 100 : d.admix
    return `
      <div class="section-title">四、 配合比关键参数</div>
      <table class="compact">
        <thead><tr><th>水胶比 W/B</th><th>水泥/%</th><th>粉煤灰/%</th><th>微珠/%</th><th>硅灰/%</th><th>胶材总量</th><th>钢纤维/%</th><th>砂胶比</th><th>外加剂/%</th><th></th></tr></thead>
        <tbody><tr class="yellow"><td>${fmtVal(wb, 2)}</td><td>${percent(d.mmc, binder, d.cementPct)}</td><td>${percent(d.mm1, binder, d.p1)}</td><td>${percent(d.mm3, binder, d.p3)}</td><td>${percent(d.mm4, binder, d.p4)}</td><td>${fmtVal(binder, 0)}</td><td>${fmtVal(d.sf_vol, 2)}</td><td>${fmtVal(d.sb, 2)}</td><td>${fmtVal(admix, 2)}</td><td></td></tr></tbody>
      </table>`
  }
  const binder = hpcBinderTotal(d)
  const water = num(d.mmw)
  const coarse = num(d.mmg)
  const sand = num(d.mms)
  const coarseDensity = num(d.rhog)
  const admixtureMass = num(d.mma)
  const wb = water !== null && binder !== null && binder > 0 ? water / binder : d.wb
  const sandTotal = sumValues([d.mmg, d.mms])
  const sandRate = sand !== null && sandTotal !== null && sandTotal > 0 ? (sand / sandTotal) * 100 : d.sandR
  const vg = num(d.vg) ?? (coarse !== null && coarseDensity !== null && coarseDensity > 0 ? coarse / coarseDensity : null)
  const admix = admixtureMass !== null && binder !== null && binder > 0 ? (admixtureMass / binder) * 100 : d.admix
  return `
    <div class="section-title">四、 配合比关键参数</div>
    <table class="compact">
      <thead><tr><th>水胶比 W/B</th><th>水泥/%</th><th>粉煤灰/%</th><th>矿粉/%</th><th>微珠/%</th><th>硅灰/%</th><th>胶材总量</th><th>砂率/%</th><th>粗骨料体积 /m³</th><th>外加剂/%</th><th>含气量/m3</th></tr></thead>
      <tbody><tr class="yellow"><td>${fmtVal(wb, 2)}</td><td>${percent(d.mmc, binder, d.cementPct)}</td><td>${percent(d.mm1, binder, d.p1)}</td><td>${percent(d.mm2, binder, d.p2)}</td><td>${percent(d.mm3, binder, d.p3)}</td><td>${percent(d.mm4, binder, d.p4)}</td><td>${fmtVal(binder, 0)}</td><td>${fmtVal(sandRate, 0)}</td><td>${fmtVal(vg, 2)}</td><td>${fmtVal(admix, 2)}</td><td>${fmtVal(d.airContent, 2)}</td></tr></tbody>
    </table>`
}

function buildFinalMixSection(d: ReportData): string {
  if (d.isUHPC) {
    const perM3 = [d.mmc, d.mm1, d.mm3, d.mm4, d.mms, d.msf, d.mmw, d.mma]
    const total = totalMass(d, perM3)
    return `
      <div class="section-title">五、 实验室配合比</div>
      <table class="compact">
        <thead><tr><th>用量</th><th>水泥</th><th>粉煤灰</th><th>微珠</th><th>硅灰</th><th>细骨料</th><th>钢纤维</th><th>水</th><th>外加剂</th><th>合计</th></tr></thead>
        <tbody>
          <tr class="green"><td>每方用量(kg/m³)</td><td>${fmtVal(d.mmc)}</td><td>${fmtVal(d.mm1)}</td><td>${fmtVal(d.mm3)}</td><td>${fmtVal(d.mm4)}</td><td>${fmtVal(d.mms)}</td><td>${fmtVal(d.msf)}</td><td>${fmtVal(d.mmw)}</td><td>${fmtVal(d.mma)}</td><td>${total}</td></tr>
          <tr class="yellow"><td>试拌用量(kg/${d.vBatch}L)</td><td>${scaled(d.mmc, d.vBatch)}</td><td>${scaled(d.mm1, d.vBatch)}</td><td>${scaled(d.mm3, d.vBatch)}</td><td>${scaled(d.mm4, d.vBatch)}</td><td>${scaled(d.mms, d.vBatch)}</td><td>${scaled(d.msf, d.vBatch)}</td><td>${scaled(d.mmw, d.vBatch)}</td><td>${scaled(d.mma, d.vBatch)}</td><td>${scaled(total, d.vBatch)}</td></tr>
        </tbody>
      </table>`
  }
  const perM3 = [d.mmc, d.mm1, d.mm2, d.mm3, d.mm4, d.mmg, d.mms, d.mmw, d.mma]
  const total = totalMass(d, perM3)
  return `
    <div class="section-title">五、 实验室配合比</div>
    <table class="compact">
      <thead><tr><th>用量</th><th>水泥</th><th>粉煤灰</th><th>矿粉</th><th>微珠</th><th>硅灰</th><th>粗骨料</th><th>细骨料</th><th>水</th><th>外加剂</th><th>合计</th></tr></thead>
      <tbody>
        <tr class="green"><td>每方用量(kg/m³)</td><td>${fmtVal(d.mmc)}</td><td>${fmtVal(d.mm1)}</td><td>${fmtVal(d.mm2)}</td><td>${fmtVal(d.mm3)}</td><td>${fmtVal(d.mm4)}</td><td>${fmtVal(d.mmg)}</td><td>${fmtVal(d.mms)}</td><td>${fmtVal(d.mmw)}</td><td>${fmtVal(d.mma)}</td><td>${total}</td></tr>
        <tr class="yellow"><td>试拌用量(kg/${d.vBatch}L)</td><td>${scaled(d.mmc, d.vBatch)}</td><td>${scaled(d.mm1, d.vBatch)}</td><td>${scaled(d.mm2, d.vBatch)}</td><td>${scaled(d.mm3, d.vBatch)}</td><td>${scaled(d.mm4, d.vBatch)}</td><td>${scaled(d.mmg, d.vBatch)}</td><td>${scaled(d.mms, d.vBatch)}</td><td>${scaled(d.mmw, d.vBatch)}</td><td>${scaled(d.mma, d.vBatch)}</td><td>${scaled(total, d.vBatch)}</td></tr>
      </tbody>
    </table>`
}

function buildEvaluationSection(d: ReportData): string {
  const strengthMult = d.isUHPC ? 1.10 : 1.15
  const workabilityRef = getHpcWorkabilityReference(d.vgReferenceCode)
  const spreadReqText = d.evalSpreadReq != null
    ? fmtVal(d.evalSpreadReq, 0) + ' mm'
    : (d.reqSpread != null ? fmtVal(d.reqSpread, 0) + ' mm' : (workabilityRef?.metric === 'spread' ? workabilityRef.desc : '—'))
  return `
    <div class="section-title">六、 混凝土性能评价</div>
    <table>
      <thead><tr><th colspan="2">指标</th><th>实测值</th><th>要求</th><th>评价</th></tr></thead>
      <tbody>
        <tr><td class="cat" rowspan="3">工作性能</td><td>坍落度/mm</td><td>${textVal(d.evalSlump)}</td><td>${d.reqSlump != null ? fmtVal(d.reqSlump, 0) + ' mm' : (workabilityRef?.metric === 'slump' ? workabilityRef.desc : '—')}</td><td rowspan="3">${passLabel(d.workabilityPass)}</td></tr>
        <tr><td>扩展度/mm</td><td>${textVal(d.evalSpread)}</td><td>${spreadReqText}</td></tr>
        <tr><td>综合性描述</td><td>${textVal(d.workDesc)}</td><td>和易性良好；不离析、不泌水</td></tr>
        <tr><td class="cat" rowspan="2">抗压强度</td><td>平均值/MPa</td><td>${d.strengthOverallAvg !== null ? d.strengthOverallAvg.toFixed(1) : '—'}</td><td>≥ ${strengthMult.toFixed(2)}×强度等级${Number.isFinite(d.strengthGradeNum) ? '(' + (d.strengthGradeNum * strengthMult).toFixed(1) + ' MPa)' : ''}</td><td rowspan="2">${passLabel(d.strengthPass)}</td></tr>
        <tr><td>最小值/MPa</td><td>${d.strengthMinGroupAvg !== null ? d.strengthMinGroupAvg.toFixed(1) : '—'}</td><td>≥ 0.95×强度等级${Number.isFinite(d.strengthGradeNum) ? '(' + (d.strengthGradeNum * 0.95).toFixed(1) + ' MPa)' : ''}</td></tr>
      </tbody>
    </table>`
}

export function generateReportHtml(d: ReportData): string {
  const printTimeStr = new Date().toLocaleString('zh-CN')
  return `<!DOCTYPE html><html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>配合比记录 - ${d.record.name}</title>
<style>
  @page { size: A4 landscape; margin: 8mm; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif; font-size: 8pt; color: #1f2933; background: #fff; line-height: 1.22; }
  .page-container { width: 277mm; margin: 0 auto; padding: 1mm 2mm 0; }
  .report-header { border-bottom: 2px solid #2f5597; margin-bottom: 5px; padding-bottom: 4px; }
  .report-title { text-align: center; font-size: 15pt; font-weight: 800; color: #1f4e79; letter-spacing: 1px; }
  .report-subtitle { margin-top: 2px; text-align: center; font-size: 7.2pt; color: #667085; }
  .section-title { margin: 5px 0 3px; padding: 3px 7px; border-left: 4px solid #2f5597; background: #f1f4f8; color: #1f4e79; font-size: 8.5pt; font-weight: 800; }
  table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 3px; border: 1px solid #c9d2df; }
  th, td { border: 1px solid #d6dde8; padding: 2.4px 3px; text-align: center; vertical-align: middle; word-break: break-word; }
  th { background: #eef2f7; color: #344054; font-weight: 700; }
  .green td, tr.green td { background: #fbfcfe; }
  .yellow td, tr.yellow td { background: #fffdf3; }
  .compact th, .compact td { font-size: 7.4pt; padding: 2px 2.2px; }
  .cat { background: #f4f6f8; font-weight: 700; }
  .pass { color: #0f5132; font-weight: 700; }
  .fail { color: #842029; font-weight: 700; }
  .footer { margin-top: 4px; padding-top: 3px; border-top: 1px solid #d6dde8; font-size: 6.8pt; color: #667085; text-align: right; }
  @media print {
    th, .green td, .yellow td, .section-title { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  }
</style>
</head>
<body>
<div class="page-container">
  <div class="report-header">
    <div class="report-title">混凝土配合比记录报告</div>
    <div class="report-subtitle">${d.record.name} · ${d.categoryLabel} · ${d.fmtDate}</div>
  </div>
  ${buildInfoSection(d)}
  ${buildRequirementSection(d)}
  ${buildRawMaterialSection(d)}
  ${buildKeyParamsSection(d)}
  ${buildFinalMixSection(d)}
  ${buildEvaluationSection(d)}
  <div class="footer">${d.project?.project_name ?? ''}${d.project?.project_code ? ' / ' + d.project.project_code : ''} · 打印时间：${printTimeStr}</div>
</div>
</body>
</html>`
}
