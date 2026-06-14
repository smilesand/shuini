import sys
import re
from pathlib import Path

path = 'd:/Code/shuini_calculator/frontend/src/views/ReportView.vue'
text = Path(path).read_text(encoding='utf-8')

match = re.search(r'function exportReport\(record: RecordItem\) \{.*?(?=onMounted\()', text, flags=re.DOTALL)
if not match:
    print("Could not match.")
    sys.exit(1)

new_code = """function exportReport(record: RecordItem) {
  const project = selectedProject.value;
  const data = record.record_data ?? {};
  
  const evalStrength = extractEval(record, 'evalStrength28d');
  const evalSlump = extractEval(record, 'evalSlump') || extractEval(record, 'slumpMeasured');
  const evalSpread = extractEval(record, 'evalSpread') || extractEval(record, 'spreadMeasured');
  const workDesc = extractEval(record, 'evalWorkabilityDesc') || extractEval(record, 'workabilityNote');

  // Dictionary for Chinese/English Abbreviations
  const keyMap: Record<string, string> = {
    cement: '水泥 (C)', fly_ash: '粉煤灰 (FA)', micro_bead: '微珠 (MB)',
    slag_powder: '矿渣粉 (SG)', silica_fume: '硅灰 (SF)', water: '用水量 (W)',
    sand: '细骨料/砂 (S)', coarse_agg: '粗骨料/石 (G)', admixture: '外加剂 (A)',
    steel_fiber: '钢纤维 (St)', binder: '胶凝材料总量 (B)', total: '混合料合计',
    mc: '水泥 (C)', m1: '矿物掺合料1', m2: '矿物掺合料2', m3: '矿物掺合料3',
    m4: '矿物掺合料4', ms: '细骨料/砂 (S)', mg: '粗骨料/石 (G)', mw: '水 (W)',
    ma: '外加剂 (A)', water_binder_ratio: '水胶比 (W/B)', sand_ratio: '砂率 (Sp)',
    design_strength: '设计强度', fcu0: '配制强度', batchVolume: '试拌体积',
    densityCorrectionFactor: '密度校正系数 (δ)', calculatedDensity: '计算表观密度',
    measuredDensity: '实测表观密度', lab_mix: '实验室配合比', design_mix: '设计配合比',
    trial_mix: '试配配合比', variant_wb_plus: '水胶比 +', variant_wb_minus: '水胶比 -',
    variant_sf_plus: '硅灰 +5%', variant_sf_minus: '硅灰 -5%', strengthMixes: '强度试配序列',
    fcuk: '强度标准值', fb: '胶凝材料强度fb', aa: '回归系数aa', ab: '回归系数ab', ac: '回归系数ac',
    r2: '相关系数R²', vg: '粗骨料体积', rhog: '粗骨料密度', beta_s: '砂率 (小数)',
    rhos: '细骨料密度', rhoc: '水泥密度', bc: '水泥质量分数', rhob: '胶凝材料密度',
    vp: '浆体体积', mb: '胶凝材料', alpha: '外加剂掺量', strength_grade: '强度等级',
    admixture_ratio: '外加剂掺量', sand_binder_ratio: '砂胶比',
    steel_fiber_volume_ratio: '钢纤维体积率', steel_fiber_density: '钢纤维密度',
    trial_sb: '试配砂胶比', trial_alpha: '试配外加剂掺量', sb: '砂胶比', sf_mass: '钢纤维质量',
    wbAdj: '水胶比校正', mbAdj: '胶凝材料校正', sandRatioAdj: '砂率校正', alphaAdj: '外加剂掺量校正',
    workabilityBinderDelta: '胶凝材料差值', workabilitySandRatioDelta: '砂率差值',
    workabilityAlphaDelta: '外加剂差值', deltaWb: '试配步长:水胶比',
    deltaBs: '试配步长:砂率', strength0: '基准水胶比抗压强度实测', strengthP: '大水胶比抗压强实测度',
    strengthN: '小水胶比抗压强实测度', recommend_wb: '建议水胶比', predict_strength: '预测抗压强度',
    sTargetStrength: '目标配制强度', base_wb: '基准水胶比', base_bs: '基准砂率',
    base_alpha: '基准外加剂掺量', beta_s_adj: '砂率调节比例', alpha_adj: '外加剂调节掺量',
    wb: '水胶比', initial: '初始值', corrected: '容重校正值',
    assumed_mix_mass: '假定拌合物表现密度', binder_volume_ratios: '胶凝材料体积比例',
    binder_mass_ratios: '胶凝材料质量比例', properties: '材料属性', b1p: '矿物掺合料1掺量',
    b2p: '矿物掺合料2掺量', b3p: '矿物掺合料3掺量', b4p: '矿物掺合料4掺量',
    rho1: '矿物掺合料1密度', rho2: '矿物掺合料2密度', rho3: '矿物掺合料3密度', rho4: '矿物掺合料4密度',
    key: '参数', label: '项目名', trial_val: '配比设定值', admixture_pct: '外加剂百分比',
    sand_total_ratio: '含砂总量之比', workability_result: '工作性结果', trial_materials: '试配材料列表',
    strength_regression: '强度回归结果', strength_mixes: '不同强度试配项', chart_data: '强度曲线数据',
    min_bw: '胶水比底限', max_bw: '胶水比上限', range_bw: '胶水比区间', min_strength: '强度基线',
    max_strength: '强度上限', a: '系数A', b: '系数B'
  };

  const unitMap: Record<string, string> = {
    cement: 'kg/m³', fly_ash: 'kg/m³', micro_bead: 'kg/m³', slag_powder: 'kg/m³', silica_fume: 'kg/m³',
    water: 'kg/m³', sand: 'kg/m³', coarse_agg: 'kg/m³', admixture: 'kg/m³', steel_fiber: 'kg/m³',
    binder: 'kg/m³', total: 'kg/m³', mc: 'kg/m³', m1: 'kg/m³', m2: 'kg/m³', m3: 'kg/m³', m4: 'kg/m³',
    ms: 'kg/m³', mg: 'kg/m³', mw: 'kg/m³', ma: 'kg/m³', design_strength: 'MPa', fcu0: 'MPa',
    batchVolume: 'L', calculatedDensity: 'kg/m³', measuredDensity: 'kg/m³', sand_ratio: '%',
    fcuk: 'MPa', fb: 'MPa', sTargetStrength: 'MPa', strength0: 'MPa', strengthP: 'MPa', strengthN: 'MPa',
    predict_strength: 'MPa', rhog: 'kg/m³', rhos: 'kg/m³', rhoc: 'kg/m³', rhob: 'kg/m³',
    steel_fiber_density: 'kg/m³', assumed_mix_mass: 'kg/m³'
  };

  const rows: string[] = [];

  function formatValue(key: string, val: unknown): string {
    if (typeof val === 'number') {
      if (['sand_ratio', 'admixture_pct'].includes(key) && val > 1) return val.toFixed(2) + ' %'; 
      if (['sand_ratio', 'admixture_pct', 'beta_s'].includes(key) && val <= 1) return (val * 100).toFixed(2) + ' %';
      if (['design_strength', 'fcu0', 'predict_strength', 'sTargetStrength'].includes(key)) return val.toFixed(1);
      if (['densityCorrectionFactor', 'alpha', 'admixture_ratio'].includes(key)) return val.toFixed(3);
      if (unitMap[key] === 'kg/m³') return val.toFixed(1);
      if (val % 1 !== 0) return val.toFixed(2);
    }
    return String(val ?? '—');
  }

  function renderKV(obj: Record<string, unknown>, indent = 0, isRoot = true): void {
    for (const [key, val] of Object.entries(obj)) {
      if (['evalStrength28d', 'evalSlump', 'evalSpread', 'evalWorkabilityDesc', 'slumpMeasured', 'spreadMeasured', 'workabilityNote'].includes(key)) continue;
      
      let label = keyMap[key] || key;
      const unit = unitMap[key] ? ` <span class="unit">[${unitMap[key]}]</span>` : '';
      const pad = '&nbsp;'.repeat(indent * 6);

      if (isRoot && (key === 'trial_data' || key === 'original_request' || key === 'inputs')) {
        rows.push(`<tr><td class="kv-key section-sub" colspan="2" style="padding-left:${indent * 12 + 12}px"><b>⬇ ${key === 'inputs' || key === 'original_request' ? '输入参数' : '试配数据 (计算结果等)'}</b></td></tr>`);
        renderKV(val as Record<string, unknown>, indent + 1, false);
      } else if (isRoot && (key === 'calculated' || key === 'calculated_mix' || key === 'outputs')) {
        rows.push(`<tr><td class="kv-key section-sub" colspan="2" style="padding-left:${indent * 12 + 12}px"><b>⬇ 计算结果 (模型侧)</b></td></tr>`);
        renderKV(val as Record<string, unknown>, indent + 1, false);
      } else if (val !== null && typeof val === 'object' && !Array.isArray(val)) {
        rows.push(`<tr><td class="kv-key" colspan="2" style="padding-left:${indent * 12 + 12}px; background:#fafafa;">${pad}<b>${label}</b></td></tr>`);
        renderKV(val as Record<string, unknown>, indent + 1, false);
      } else if (Array.isArray(val)) {
        let stringVal = val.map(v => (v !== null && typeof v === 'object' && v.label) ? v.label : (v !== null && typeof v === 'object' && v.key) ? keyMap[v.key as string]||v.key : v).join(', ');
        stringVal = stringVal.replace(/([a-zA-Z_]+)/g, m => keyMap[m]||m);
        rows.push(`<tr><td class="kv-key" style="padding-left:${indent * 12 + 12}px">${pad}<b>${label}</b></td><td class="kv-val">${stringVal}</td></tr>`);
      } else {
        rows.push(`<tr><td class="kv-key" style="padding-left:${indent * 12 + 12}px">${pad}${label}${unit}</td><td class="kv-val">${formatValue(key, val)}</td></tr>`);
      }
    }
  }

  // Inject a fix for UHPC format if needed, if it does not have .inputs but raw keys
  renderKV(data as Record<string, unknown>);

  const printTimeStr = new Date().toLocaleString('zh-CN');

  const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>配合比记录 - ${record.name}</title>
<style>
  @page { size: A4; margin: 15mm; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; font-size: 11pt; color: #000; background: #fff; line-height: 1.4; }
  .page-container { max-width: 210mm; margin: 0 auto; }
  .report-header { text-align: center; border-bottom: 2px solid #000; padding-bottom: 12px; margin-bottom: 15px; }
  .report-title { font-size: 20pt; font-weight: bold; letter-spacing: 2px; margin-bottom: 8px; }
  .report-subtitle { font-size: 10pt; color: #555; }
  .section-title { font-size: 12pt; font-weight: bold; margin: 20px 0 10px; border-left: 5px solid #1e3c72; padding-left: 8px; color: #1e3c72; background: #f4f6f9; padding-top: 4px; padding-bottom: 4px; }
  .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 20px; margin-bottom: 15px; font-size: 10pt; }
  .info-item { display: flex; border-bottom: 1px dashed #ccc; padding-bottom: 4px; }
  .info-label { font-weight: bold; width: 100px; color: #333; }
  .info-value { flex: 1; color: #000; }
  
  /* Remove page-break-inside: avoid from table to ensure long lists flow correctly into the next page */
  table { width: 100%; border-collapse: collapse; font-size: 10pt; margin-bottom: 15px; }
  tr { page-break-inside: avoid; }
  th, td { border: 1px solid #000; padding: 5px 8px; text-align: left; }
  th { background: #f0f0f0; font-weight: bold; text-align: center; }
  .kv-key { width: 55%; font-weight: 500; }
  .kv-val { font-family: Consolas, monospace; font-size: 11pt; }
  .unit { font-size: 8pt; color: #666; margin-left: 4px; font-weight: normal; }
  .section-sub { background: #f9f9f9; text-align: left; }
  .footer { margin-top: 30px; font-size: 9pt; color: #777; text-align: center; border-top: 1px solid #ccc; padding-top: 10px; }
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
    <div class="report-subtitle">系统生成报告 | 记录类别：${categoryLabel(record.category)}</div>
  </div>
  <div class="section-title">一、 项目情况信息</div>
  <div class="info-grid">
    <div class="info-item"><div class="info-label">项目名称</div><div class="info-value">${project?.project_name ?? '—'}</div></div>
    <div class="info-item"><div class="info-label">项目编号</div><div class="info-value">${project?.project_code ?? '—'}</div></div>
    <div class="info-item"><div class="info-label">记录名称</div><div class="info-value">${record.name}</div></div>
    <div class="info-item"><div class="info-label">配合比类别</div><div class="info-value">${categoryLabel(record.category)}</div></div>
    <div class="info-item"><div class="info-label">创建人</div><div class="info-value">${record.created_by}</div></div>
    <div class="info-item"><div class="info-label">创建时间</div><div class="info-value">${fmtDate(record.created_at)}</div></div>
  </div>
  <div class="section-title">二、 配合比及关键参数</div>
  <table>
    <thead><tr><th>参数名称</th><th>数值</th></tr></thead>
    <tbody>${rows.join('\\n')}</tbody>
  </table>
  <div class="section-title">三、 混凝土强度与工作性能（实验室配合比基准）</div>
  <table>
    <tbody>
      <tr><td class="kv-key">28d抗压强度 <span class="unit">[MPa]</span></td><td class="kv-val">${evalStrength || '—'}</td></tr>
      <tr><td class="kv-key">实测坍落度 <span class="unit">[mm]</span></td><td class="kv-val">${evalSlump || '—'}</td></tr>
      <tr><td class="kv-key">实测扩展度 <span class="unit">[mm]</span></td><td class="kv-val">${evalSpread || '—'}</td></tr>
      <tr><td class="kv-key">工作性及表现</td><td class="kv-val">${workDesc || '—'}</td></tr>
    </tbody>
  </table>
  <div class="footer">本记录由 水泥配合比计算系统 自动生成 · 打印时间：${printTimeStr}</div>
</div>
</body>
</html>`;

  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const win = window.open(url, '_blank');
  if (win) {
    win.addEventListener('load', () => {
      setTimeout(() => win.print(), 500);
    });
  }
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
"""

text = text[:match.start()] + new_code + text[match.end():]
Path(path).write_text(text, encoding='utf-8')
print("Successfully replaced with regex!")