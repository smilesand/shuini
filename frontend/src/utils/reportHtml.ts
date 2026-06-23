import { type RecordItem } from '../api/records'
import { type Project } from '../api/projects'
import { computeGroupValue } from '../composables/useStrengthEval'
import { getHpcWorkabilityReference } from './hpcWorkability'

// ── Types ────────────────────────────────────────────────────────
export interface ReportData {
  project: Project | null
  record: RecordItem
  categoryLabel: string
  fmtDate: string
  // Key parameters
  strengthGrade: string
  designStrength: unknown
  totalBinder: unknown
  cementPct: unknown
  p1: unknown; p2: unknown; p3: unknown; p4: unknown
  wb: unknown; sandR: unknown; sb: unknown; admix: unknown; sf_vol: unknown
  isUHPC: boolean
  // Mix materials
  mmc: unknown; mm1: unknown; mm2: unknown; mm3: unknown; mm4: unknown
  mmg: unknown; mms: unknown; mmw: unknown; mma: unknown; msf: unknown; mtot: unknown
  bmc: unknown; bm1: unknown; bm2: unknown; bm3: unknown; bm4: unknown
  bmg: unknown; bms: unknown; bmw: unknown; bma: unknown; bmsf: unknown; bmtot: unknown
  vBatch: number
  // Performance
  evalSlump: unknown; evalSpread: unknown; workDesc: unknown
  workabilityPass: boolean | null
  strengthPass: boolean | null
  vgReferenceCode: string | null
  // Design requirements (设计要求) & raw materials (原材料性能)
  reqSlump: unknown; reqSpread: unknown
  maxAggregateSize: string | null
  fb: unknown
  rhoc: unknown; rho1: unknown; rho2: unknown; rho3: unknown; rho4: unknown; rhog: unknown; rhos: unknown
  // Strength groups
  strengthGroups: { id: string; values: (number | null)[] }[]
  groupEvals: ReturnType<typeof computeGroupValue>[]
  strengthOverallAvg: number | null
  strengthMinGroupAvg: number | null
  strengthGradeNum: number
  targetForEval: unknown
}

// ── Helpers ──────────────────────────────────────────────────────
function fmtVal(v: unknown, digits = 2): string {
  if (typeof v === 'number' && Number.isFinite(v)) return v.toFixed(digits)
  return '—'
}

function passLabel(pass: boolean | null): string {
  if (pass === true) return '<span style="color:#0f5132;font-weight:bold;">合格 ✓</span>'
  if (pass === false) return '<span style="color:#842029;font-weight:bold;">不合格 ✗</span>'
  return '—'
}

// ── Table generation ─────────────────────────────────────────────
function buildKeyParamsTable(d: ReportData): { head: string; body: string } {
  if (!d.isUHPC) {
    const head = `<tr><th>类型</th><th>强度等级</th><th>配制强度/MPa</th><th>胶凝总量/kg</th><th>水泥/%</th><th>粉煤灰/%</th><th>矿粉/%</th><th>微珠/%</th><th>硅灰/%</th><th>水胶比</th><th>砂率/%</th><th>外加剂/%</th></tr>`
    const body = `<tr>
      <td>HPC</td>
      <td>${d.strengthGrade === '—' ? 'C80' : d.strengthGrade}</td>
      <td>${fmtVal(d.designStrength, 1)}</td>
      <td>${fmtVal(d.totalBinder, 1)}</td>
      <td>${fmtVal(d.cementPct, 1)}</td>
      <td>${fmtVal(d.p1, 1)}</td>
      <td>${fmtVal(d.p2, 1)}</td>
      <td>${fmtVal(d.p3, 1)}</td>
      <td>${fmtVal(d.p4, 1)}</td>
      <td>${fmtVal(d.wb, 3)}</td>
      <td>${fmtVal(d.sandR, 1)}</td>
      <td>${fmtVal(d.admix, 2)}</td>
    </tr>`
    return { head, body }
  }
  const head = `<tr><th>类型</th><th>强度等级</th><th>配制强度/MPa</th><th>胶凝总量/kg</th><th>水泥/%</th><th>粉煤灰/%</th><th>微珠/%</th><th>硅灰/%</th><th>钢纤维/%</th><th>砂胶比</th><th>外加剂/%</th></tr>`
  const body = `<tr>
    <td>UHPC</td>
    <td>${d.strengthGrade === '—' ? 'C130' : d.strengthGrade}</td>
    <td>${fmtVal(d.designStrength, 1)}</td>
    <td>${fmtVal(d.totalBinder, 1)}</td>
    <td>${String(d.cementPct) !== '—' ? fmtVal(d.cementPct, 1) : '—'}</td>
    <td>${fmtVal(d.p1, 1)}</td>
    <td>${fmtVal(d.p3, 1)}</td>
    <td>${fmtVal(d.p4, 1)}</td>
    <td>${fmtVal(d.sf_vol, 1)}</td>
    <td>${fmtVal(d.sb, 2)}</td>
    <td>${fmtVal(d.admix, 2)}</td>
  </tr>`
  return { head, body }
}

function buildFinalMixTable(d: ReportData): { head: string; body1: string; body2: string } {
  if (!d.isUHPC) {
    const head = `<tr><th>状态</th><th>水泥</th><th>粉煤灰</th><th>矿粉</th><th>微珠</th><th>硅灰</th><th>粗骨料</th><th>细骨料</th><th>水</th><th>外加剂</th><th>合计</th></tr>`
    const body1 = `<tr><td>每方用量(kg/m³)</td><td>${fmtVal(d.mmc)}</td><td>${fmtVal(d.mm1)}</td><td>${fmtVal(d.mm2)}</td><td>${fmtVal(d.mm3)}</td><td>${fmtVal(d.mm4)}</td><td>${fmtVal(d.mmg)}</td><td>${fmtVal(d.mms)}</td><td>${fmtVal(d.mmw)}</td><td>${fmtVal(d.mma)}</td><td>${fmtVal(d.mtot)}</td></tr>`
    const body2 = `<tr><td>试拌用量(kg/${d.vBatch}L)</td><td>${fmtVal(d.bmc)}</td><td>${fmtVal(d.bm1)}</td><td>${fmtVal(d.bm2)}</td><td>${fmtVal(d.bm3)}</td><td>${fmtVal(d.bm4)}</td><td>${fmtVal(d.bmg)}</td><td>${fmtVal(d.bms)}</td><td>${fmtVal(d.bmw)}</td><td>${fmtVal(d.bma)}</td><td>${fmtVal(d.bmtot)}</td></tr>`
    return { head, body1, body2 }
  }
  const head = `<tr><th>状态</th><th>水泥</th><th>粉煤灰</th><th>微珠</th><th>硅灰</th><th>细骨料(砂)</th><th>钢纤维</th><th>水</th><th>外加剂</th><th>合计</th></tr>`
  const body1 = `<tr><td>每方用量(kg/m³)</td><td>${fmtVal(d.mmc)}</td><td>${fmtVal(d.mm1)}</td><td>${fmtVal(d.mm3)}</td><td>${fmtVal(d.mm4)}</td><td>${fmtVal(d.mms)}</td><td>${fmtVal(d.msf)}</td><td>${fmtVal(d.mmw)}</td><td>${fmtVal(d.mma)}</td><td>${fmtVal(d.mtot)}</td></tr>`
  const body2 = `<tr><td>试拌用量(kg/${d.vBatch}L)</td><td>${fmtVal(d.bmc)}</td><td>${fmtVal(d.bm1)}</td><td>${fmtVal(d.bm3)}</td><td>${fmtVal(d.bm4)}</td><td>${fmtVal(d.bms)}</td><td>${fmtVal(d.bmsf)}</td><td>${fmtVal(d.bmw)}</td><td>${fmtVal(d.bma)}</td><td>${fmtVal(d.bmtot)}</td></tr>`
  return { head, body1, body2 }
}

// ── 性能要求 / 原材料性能 表 ──────────────────────────────────────
function buildPerfReqTable(d: ReportData): string {
  const grade = d.strengthGrade && d.strengthGrade !== '—' ? d.strengthGrade : '—'
  const spread = fmtVal(d.reqSpread, 0)
  const slump = fmtVal(d.reqSlump, 0)
  return `<table>
    <thead>
      <tr><th>项目</th><th>强度等级/MPa</th><th>扩展度/mm</th><th>坍落度/mm</th></tr>
    </thead>
    <tbody>
      <tr><td>要求</td><td>${grade}</td><td>${spread}</td><td>${slump}</td></tr>
    </tbody>
  </table>`
}

function buildRawMaterialTable(d: ReportData): string {
  return `<table>
    <thead>
      <tr>
        <th rowspan="2">胶材28d强度/MPa</th>
        <th colspan="7">表观密度/kg/m³</th>
        <th rowspan="2">粗骨料最大粒径/mm</th>
      </tr>
      <tr>
        <th>水泥</th><th>粉煤灰</th><th>矿粉</th><th>微珠</th><th>硅灰</th><th>粗骨料</th><th>细骨料</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>${fmtVal(d.fb, 1)}</td>
        <td>${fmtVal(d.rhoc, 0)}</td>
        <td>${fmtVal(d.rho1, 0)}</td>
        <td>${fmtVal(d.rho2, 0)}</td>
        <td>${fmtVal(d.rho3, 0)}</td>
        <td>${fmtVal(d.rho4, 0)}</td>
        <td>${fmtVal(d.rhog, 0)}</td>
        <td>${fmtVal(d.rhos, 0)}</td>
        <td>${d.maxAggregateSize ?? '—'}</td>
      </tr>
    </tbody>
  </table>`
}

// ── Main export ──────────────────────────────────────────────────
export function generateReportHtml(d: ReportData): string {
  const table1 = buildKeyParamsTable(d)
  const table2 = buildFinalMixTable(d)
  const printTimeStr = new Date().toLocaleString('zh-CN')
  const strengthDesc = '每组 3 个试件。当最大值或最小值中有一个与中间值的差值超过中间值的15%时，剔除最大及最小值取中间值；当最大值和最小值与中间值的差值均超过中间值的15%时，该组试验结果无效。'

  const workabilityRef = getHpcWorkabilityReference(d.vgReferenceCode)

  return `<!DOCTYPE html><html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>配合比记录 - ${d.record.name}</title>
<style>
  @page { size: A4; margin: 10mm; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; font-size: 10.5pt; color: #000; background: #fff; line-height: 1.2; }
  .page-container { max-width: 210mm; margin: 0 auto; }
  .report-header { text-align: center; border-bottom: 2px solid #000; padding-bottom: 6px; margin-bottom: 8px; }
  .report-title { font-size: 17pt; font-weight: bold; letter-spacing: 2px; margin-bottom: 3px; }
  .report-subtitle { font-size: 9.5pt; color: #555; }
  .section-title { font-size: 11pt; font-weight: bold; margin: 9px 0 4px; border-left: 5px solid #1e3c72; padding-left: 8px; color: #1e3c72; background: #f4f6f9; padding-top: 2px; padding-bottom: 2px; }
  .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 3px 20px; margin-bottom: 8px; font-size: 9.5pt; }
  .info-item { display: flex; border-bottom: 1px dashed #ccc; padding-bottom: 2px; }
  .info-label { font-weight: bold; width: 100px; color: #333; }
  .info-value { flex: 1; color: #000; }
  table { width: 100%; border-collapse: collapse; font-size: 9.5pt; margin-bottom: 8px; }
  tr { page-break-inside: avoid; }
  th, td { border: 1px solid #000; padding: 3px 6px; text-align: center; vertical-align: middle; }
  th { background: #f0f0f0; font-weight: bold; }
  .kv-key { width: 55%; font-weight: 500; text-align: left; }
  .kv-val { font-family: Consolas, monospace; font-size: 10.5pt; }
  .unit { font-size: 8pt; color: #666; margin-left: 4px; font-weight: normal; }
  .section-sub { background: #f9f9f9; }
  .cat-cell { font-weight: bold; background: #f5f7fa; width: 70px; }
  .key-params th, .key-params td { font-size: 7.5pt; white-space: nowrap; padding: 3px 3px; }
  .eval-table td:nth-child(5), .eval-table th:nth-child(5) { width: 80px; }
  b { display: inline-block; margin: 2px 0 1px; }
  .footer { margin-top: 12px; font-size: 8.5pt; color: #777; text-align: center; border-top: 1px solid #ccc; padding-top: 6px; }
  @media print {
    body { font-size: 10pt; }
    .page-container { width: 100%; }
    th { -webkit-print-color-adjust: exact; background-color: #f0f0f0 !important; }
    .section-title { -webkit-print-color-adjust: exact; background-color: #f4f6f9 !important; border-left-color: #1e3c72 !important; }
  }
</style>
</head>
<body>
<div class="page-container">
  <div class="report-header">
    <div class="report-title">混凝土配合比记录</div>
    <div class="report-subtitle">系统生成报告 | 记录类别：${d.categoryLabel}</div>
  </div>
  <div class="section-title">一、 项目情况信息</div>
  <div class="info-grid">
    <div class="info-item"><div class="info-label">项目名称</div><div class="info-value">${d.project?.project_name ?? '—'}</div></div>
    <div class="info-item"><div class="info-label">项目编号</div><div class="info-value">${d.project?.project_code ?? '—'}</div></div>
    <div class="info-item"><div class="info-label">记录名称</div><div class="info-value">${d.record.name}</div></div>
    <div class="info-item"><div class="info-label">配合比类别</div><div class="info-value">${d.categoryLabel}</div></div>
    <div class="info-item"><div class="info-label">创建人</div><div class="info-value">${d.record.created_by}</div></div>
    <div class="info-item"><div class="info-label">创建时间</div><div class="info-value">${d.fmtDate}</div></div>
  </div>
  <div class="section-title">二、 性能要求与原材料性能</div>
  <b>性能要求</b>
  ${buildPerfReqTable(d)}
  <b>原材料性能</b>
  ${buildRawMaterialTable(d)}
  <div class="section-title">三、 配合比及相关记录</div>
  <b>配合比关键参数</b>
  <table class="key-params">
    <thead>${table1.head}</thead>
    <tbody>${table1.body}</tbody>
  </table>
  <b>最终配合比</b>
  <table>
    <thead>${table2.head}</thead>
    <tbody>${table2.body1}
${table2.body2}</tbody>
  </table>
  <div class="section-title">四、 混凝土性能评价</div>
  <table class="eval-table">
    <thead>
      <tr><th colspan="2">指标</th><th>实测值</th><th>要求</th><th>评价</th></tr>
    </thead>
    <tbody>
      <tr>
        <td class="cat-cell" rowspan="3">工作性能</td>
        <td>坍落度/mm</td>
        <td>${d.evalSlump || '—'}</td>
        <td>${d.reqSlump != null ? fmtVal(d.reqSlump, 0) + ' mm' : (workabilityRef?.metric === 'slump' ? workabilityRef.desc : '')}</td>
        <td rowspan="3">${passLabel(d.workabilityPass)}</td>
      </tr>
      <tr>
        <td>扩展度/mm</td>
        <td>${d.evalSpread || '—'}</td>
        <td>${d.reqSpread != null ? fmtVal(d.reqSpread, 0) + ' mm' : (workabilityRef?.metric === 'spread' ? workabilityRef.desc : '')}</td>
      </tr>
      <tr>
        <td>综合性描述</td>
        <td style="font-size:9pt">${d.workDesc || '—'}</td>
        <td style="font-size:9pt;color:#555">和易性良好<br>不离析、不泌水</td>
      </tr>
      <tr>
        <td class="cat-cell" rowspan="2">抗压强度</td>
        <td>平均值/MPa</td>
        <td>${d.strengthOverallAvg !== null ? d.strengthOverallAvg.toFixed(1) : '—'}</td>
        <td style="font-size:9pt">≥ 1.15×强度等级${Number.isFinite(d.strengthGradeNum) ? '(' + (d.strengthGradeNum * 1.15).toFixed(1) + ' MPa)' : ''}</td>
        <td rowspan="2">${passLabel(d.strengthPass)}</td>
      </tr>
      <tr>
        <td>最小值/MPa</td>
        <td>${d.strengthMinGroupAvg !== null ? d.strengthMinGroupAvg.toFixed(1) : '—'}</td>
        <td style="font-size:9pt">≥ 0.95×强度等级${Number.isFinite(d.strengthGradeNum) ? '(' + (d.strengthGradeNum * 0.95).toFixed(1) + ' MPa)' : ''}</td>
      </tr>
    </tbody>
  </table>
  <div class="footer">本记录由 中国中车风电混塔用混凝土配合比设计系统 自动生成 · 打印时间：${printTimeStr}</div>
</div>
</body>
</html>`
}
