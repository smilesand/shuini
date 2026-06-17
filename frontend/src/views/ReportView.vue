<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listProjects, listProjectRecords, type Project } from '../api/projects'
import { type RecordItem } from '../api/records'
import RecordTable from '../components/RecordTable.vue'

const projects = ref<Project[]>([])
const loadingProjects = ref(false)
const selectedProject = ref<Project | null>(null)
const records = ref<RecordItem[]>([])
const loadingRecords = ref(false)
const projectSearch = ref('')

async function fetchProjects() {
  loadingProjects.value = true
  try {
    const res = await listProjects(projectSearch.value || undefined, 1, 100)
    projects.value = res.items
  } catch {
    ElMessage.error('加载项目列表失败')
  } finally {
    loadingProjects.value = false
  }
}

async function selectProject(project: Project) {
  selectedProject.value = project
  loadingRecords.value = true
  records.value = []
  try {
    records.value = await listProjectRecords(project.id)
  } catch {
    ElMessage.error('加载记录失败')
  } finally {
    loadingRecords.value = false
  }
}

function categoryLabel(cat: string) {
  if (cat === 'uhpc') return 'UHPC'
  if (cat === 'hpc') return 'HPC'
  if (cat === 'hpc_trial') return 'HPC试配'
  if (cat === 'uhpc_trial') return 'UHPC试配'
  return cat
}

function fmtDate(value: string) {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

function extractEval(record: RecordItem, key: string) {
  const trialData = record.record_data?.trial_data as any;
  if (!trialData) return '';
  const val = trialData.inputs ? trialData.inputs[key] : trialData[key];
  if (val === null || val === undefined) return '';
  return val;
}

// ── Export report ─────────────────────────────────────────────
function exportReport(record: RecordItem) {
  const project = selectedProject.value;
  const data = record.record_data ?? {};
  
  const evalStrength = extractEval(record, 'evalStrength28d');
  const evalSlump = extractEval(record, 'evalSlump') || extractEval(record, 'slumpMeasured');
  const evalSpread = extractEval(record, 'evalSpread') || extractEval(record, 'spreadMeasured');
  const workDesc = extractEval(record, 'evalWorkabilityDesc') || extractEval(record, 'workabilityNote');

  // Dictionary for Chinese/English Abbreviations
  const keyMap: Record<string, string> = {
    // Basic Materials
    cement: '水泥(C)', fly_ash: '粉煤灰(FA)', flyAsh: '粉煤灰(FA)', micro_bead: '微珠(MB)', microBead: '微珠(MB)',
    slag_powder: '矿渣粉(SG)', silica_fume: '硅灰(SF)', silicaFume: '硅灰(SF)', water: '用水量(W)',
    sand: '细骨料/砂(S)', coarse_agg: '粗骨料/石(G)', admixture: '外加剂(A)',
    steel_fiber: '钢纤维(St)', steelFiber: '钢纤维(St)', binder: '胶凝材料总量(B)', total: '混合料合计',
    mc: '水泥(C)', m1: '矿物掺合料1', m2: '矿物掺合料2', m3: '矿物掺合料3',
    m4: '矿物掺合料4', ms: '细骨料/砂(S)', mg: '粗骨料/石(G)', mw: '水(W)', ma: '外加剂(A)', 

    // Ratios & Properties (Backend & Frontend cases)
    water_binder_ratio: '水胶比(W/B)', waterBinderRatio: '水胶比(W/B)', 
    sand_ratio: '砂率(Sp)', sandRatio: '砂率(Sp)', sandBinderRatio: '砂胶比',
    design_strength: '设计强度', fcu0: '配制强度', batchVolume: '试拌体积',
    densityCorrectionFactor: '密度校正系数(δ)', calculatedDensity: '计算表观密度',
    measuredDensity: '实测表观密度', lab_mix: '实验室配合比', labMix: '实验室配合比',
    design_mix: '设计配合比', designMix: '设计配合比', design_data: '设计参数/数据',
    trial_mix: '试配配合比', trialMix: '试配配合比', trial_data: '试配数据',
    strengthMixes: '强度试配序列', strength_mixes: '不同强度试配项',
    strengthRegression: '强度回归计算', chartData: '图表数据',
    fcuk: '强度标准值', fb: '胶凝材料强度fb', aa: '回归系数aa', ab: '回归系数ab', ac: '回归系数ac',
    r2: '相关系数R²', vg: '粗骨料体积', rhog: '粗骨料密度', beta_s: '砂率(小数)',
    rhos: '细骨料密度', rhoc: '水泥密度', bc: '水泥质量分数', rhob: '胶凝材料密度',
    vp: '浆体体积', mb: '胶凝材料', alpha: '外加剂掺量', strength_grade: '强度等级', strengthGrade: '强度等级',
    admixture_ratio: '外加剂掺量', admixtureRatio: '外加剂掺量',
    steel_fiber_volume_ratio: '钢纤维体积率', steelFiberVolumeRatio: '钢纤维体积率',
    fiberStrengthGrade: '纤维抗拉强度等级', 
    maxParticleSize: '最大粒径', minParticleSize: '最小粒径', distributionIndex: '分布模数(q)',
    flyAshPeakSize: '粉煤灰峰值粒径', flyAshAccumulationSize: '粉煤灰堆积粒径', 
    microBeadPeakSize: '微珠峰值粒径', microBeadSilicaFumeRatio: '微珠比硅灰',
    cementDensity: '水泥密度', flyAshDensity: '粉煤灰密度', microBeadDensity: '微珠密度', 
    silicaFumeDensity: '硅灰密度', microPowderCoefficient: '微粉系数', 
    assumedMixMass: '假定拌合物表观密度', assumed_mix_mass: '假定拌合物表观密度',
    steel_fiber_density: '钢纤维密度', steelFiberDensity: '钢纤维密度',
    
    // Trial parameters
    trial_sb: '试配砂胶比', trial_alpha: '试配外加剂掺量', sb: '砂胶比', sf_mass: '钢纤维质量',
    wbAdj: '水胶比校正', mbAdj: '胶凝材料校正', sandRatioAdj: '砂率校正', alphaAdj: '外加剂掺量校正',
    workabilityBinderDelta: '胶凝材料差值', workabilitySandRatioDelta: '砂率差值',
    workabilityAlphaDelta: '外加剂差值', deltaWb: '试配步长-水胶比', deltaBs: '试配步长-砂率', 
    strength0: '基准配合比实测强度', strengthP: '大水胶实测强度', strengthN: '小水胶实测强度', 
    recommend_wb: '建议水胶比', recommendWb: '建议水胶比', 
    predict_strength: '预测抗压强度', predictStrength: '预测抗压强度',
    sTargetStrength: '目标配制强度', designStrength: '计算配制强度',
    base_wb: '基准水胶比', baseWb: '基准水胶比', 
    base_bs: '基准砂率', baseBs: '基准砂率',
    base_alpha: '基准外加剂掺量', baseAlpha: '基准外加剂掺量', 
    beta_s_adj: '砂率调节比例', alpha_adj: '外加剂调节掺量',
    wb: '水胶比', initial: '初始值', corrected: '容重校正值', version: '数据版本', inputs: '输入参数', calculated: '模型计算数据',

    // Calculated fields & Structure keys
    binder_volume_ratios: '胶凝材料体积比例', binderVolumeRatios: '胶凝材料体积比',
    binder_mass_ratios: '胶凝材料质量比例', binderMassRatios: '胶凝材料质量比',
    materialMasses: '每立方米材料用量', 
    properties: '材料属性', b1p: '外加细粉1', b2p: '外加细粉2', b3p: '外加细粉3', b4p: '外加细粉4',
    rho1: '粉料1密度', rho2: '粉料2密度', rho3: '粉料3密度', rho4: '粉料4密度',
    key: '参数', label: '项目名', trial_val: '配比设定值', trialVal: '配比设定值', admixture_pct: '外加剂百分比',
    sand_total_ratio: '含砂总量之比', workability_result: '工作性结果', workabilityResult: '工作性调整结果',
    trial_materials: '试配材料列表', trialMatCols: '试配材料调整列',
    strength_regression: '强度回归结果', chart_data: '强度曲线数据',
    min_bw: '胶水比底限', minBW: '最小水胶比', 
    max_bw: '胶水比上限', maxBW: '最大水胶比', 
    range_bw: '胶水比区间', rangeBW: '水胶比区间', 
    min_strength: '强度基线', minStrength: '最小强度',
    max_strength: '强度上限', maxStrength: '最大强度', rangeStrength: '强度区间',
    bwRatios: '水胶比序列', strengths: '强度序列',
    a: '系数A', b: '系数B',

    // API Design Keys
    mixProportion: '配比计算结果', performance: '预计性能', cost_estimate: '预计成本', notes: '备注说明',
    estimated_strength: '预计抗压强度', estimated_slump: '预计扩展度',
    slumpMeasured: '实测坍落度', spreadMeasured: '实测扩展度',
    workabilityOk: '工作性合格', workabilityNote: '工作性说明',
    adaptResult: '表观密度校正结果', original_request: '初始请求参数', outputs: '输出数据'
  };

  const unitMap: Record<string, string> = {
    cement: 'kg/m³', fly_ash: 'kg/m³', flyAsh: 'kg/m³', micro_bead: 'kg/m³', microBead: 'kg/m³',
    slag_powder: 'kg/m³', silica_fume: 'kg/m³', silicaFume: 'kg/m³', water: 'kg/m³',
    sand: 'kg/m³', coarse_agg: 'kg/m³', admixture: 'kg/m³', steel_fiber: 'kg/m³', steelFiber: 'kg/m³',
    binder: 'kg/m³', total: 'kg/m³', mc: 'kg/m³', m1: 'kg/m³', m2: 'kg/m³', m3: 'kg/m³', m4: 'kg/m³',
    ms: 'kg/m³', mg: 'kg/m³', mw: 'kg/m³', ma: 'kg/m³', design_strength: 'MPa', fcu0: 'MPa',
    batchVolume: 'L', calculatedDensity: 'kg/m³', measuredDensity: 'kg/m³', sand_ratio: '%', sandRatio: '%',
    fcuk: 'MPa', fb: 'MPa', sTargetStrength: 'MPa', designStrength: 'MPa', 
    strength0: 'MPa', strengthP: 'MPa', strengthN: 'MPa', predict_strength: 'MPa', predictStrength: 'MPa',
    estimated_strength: 'MPa', estimated_slump: 'mm',
    rhog: 'kg/m³', rhos: 'kg/m³', rhoc: 'kg/m³', rhob: 'kg/m³',
    steel_fiber_density: 'kg/m³', steelFiberDensity: 'kg/m³', assumed_mix_mass: 'kg/m³', assumedMixMass: 'kg/m³',
    cementDensity: 'kg/m³', flyAshDensity: 'kg/m³', microBeadDensity: 'kg/m³', silicaFumeDensity: 'kg/m³',
    slumpMeasured: 'mm', spreadMeasured: 'mm', maxParticleSize: 'mm', minParticleSize: 'mm'
  };

  
  function fmtVal(v: unknown, digits = 2) {
    if (typeof v === 'number' && Number.isFinite(v)) return v.toFixed(digits);
    return '—';
  }

  // Flatten the data object first so we can easily search for keys no matter where they are nested
  const flatData: Record<string, any> = {};
  function flattenObj(obj: any) {
    if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return;
    for (const [k, v] of Object.entries(obj)) {
      if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
        flattenObj(v);
      } else {
        flatData[k] = v;
      }
    }
  }
  flattenObj(data);

  // Fallbacks across different versions
  const strengthGrade = flatData.strengthGrade || flatData.strength_grade || flatData.fcuk || '—';
  const designStrength = flatData.fcu0 || flatData.designStrength || flatData.design_strength || flatData.sTargetStrength || '—';
  const totalBinder = flatData.mb || flatData.total_binder || (flatData.binder && typeof flatData.binder === 'number' ? flatData.binder : null) || '—';
  const cementPct = flatData.bcp || flatData.bc || flatData.cement || flatData.cement_pct || flatData.cementRatio || '—'; 
  const p1 = flatData.b1p ?? flatData.flyAsh ?? flatData.fly_ash_pct ?? '—';
  const p2 = flatData.b2p ?? flatData.slagPowder ?? flatData.slag_powder_pct ?? '—';
  const p3 = flatData.b3p ?? flatData.microBead ?? flatData.micro_bead_pct ?? '—';
  const p4 = flatData.b4p ?? flatData.silicaFume ?? flatData.silica_fume_pct ?? '—';
  let wb = flatData.wbAdj ?? flatData.recWb ?? flatData.recommend_wb ?? flatData.recommendWb ?? flatData.wb ?? flatData.waterBinderRatio ?? flatData.water_binder_ratio ?? '—';
  let sandR = flatData.sandRatioAdj ?? flatData.beta_s ?? flatData.sandRatio ?? flatData.sand_ratio ?? '—';
  if (typeof sandR === 'number' && sandR < 1) sandR = sandR * 100; // convert to %
  let sb = flatData.sb ?? flatData.sandBinderRatio ?? flatData.sand_binder_ratio ?? '—';
  let admix = flatData.alphaAdj ?? flatData.alpha ?? flatData.admixtureRatio ?? flatData.admixture_ratio ?? flatData.admixture_pct ?? '—';
  if (typeof admix === 'number' && flatData.admixtureRatio === undefined && flatData.admixture_ratio === undefined && flatData.admixture_pct === undefined && admix < 1) admix = admix * 100;
  const sf_vol = flatData.steelFiberVolumeRatio ?? flatData.steel_fiber_volume_ratio ?? flatData.steelFiberVolume ?? '—';

  // Lab Mix or Design Mix
  const calc = record.record_data?.calculated as Record<string, unknown> | undefined;
  const mix: Record<string, unknown> = (calc?.labMix || calc?.lab_mix || calc?.mixProportion || calc || flatData) as Record<string, unknown>;
  const mmc = mix.mc ?? mix.cement ?? '—';
  const mm1 = mix.m1 ?? mix.flyAsh ?? mix.fly_ash ?? '—';
  const mm2 = mix.m2 ?? mix.slagPowder ?? mix.slag_powder ?? '—';
  const mm3 = mix.m3 ?? mix.microBead ?? mix.micro_bead ?? '—';
  const mm4 = mix.m4 ?? mix.silicaFume ?? mix.silica_fume ?? '—';
  const mmg = mix.mg ?? mix.coarseAgg ?? mix.coarse_agg ?? '—';
  const mms = mix.ms ?? mix.sand ?? '—';
  const mmw = mix.mw ?? mix.water ?? '—';
  const mma = mix.ma ?? mix.admixture ?? mix.admixture_mass ?? '—';
  const msf = mix.msf ?? mix.steelFiber ?? mix.steel_fiber ?? mix.steelFiberMass ?? '—';
  const mtot = mix.total ?? mix.totalMass ?? mix.total_mass ?? '—';

  // Batch Volume Mix (assuming 20L)
  const vBatch = Number(flatData.batchVolume ?? flatData.batch_volume ?? 20);
  const vScale = vBatch / 1000;
  const toNum = (v: unknown) => (typeof v === 'number' ? v : NaN);
  const bmc = mmc !== '—' ? (toNum(mmc) * vScale) : '—';
  const bm1 = mm1 !== '—' ? (toNum(mm1) * vScale) : '—';
  const bm2 = mm2 !== '—' ? (toNum(mm2) * vScale) : '—';
  const bm3 = mm3 !== '—' ? (toNum(mm3) * vScale) : '—';
  const bm4 = mm4 !== '—' ? (toNum(mm4) * vScale) : '—';
  const bmg = mmg !== '—' ? (toNum(mmg) * vScale) : '—';
  const bms = mms !== '—' ? (toNum(mms) * vScale) : '—';
  const bmw = mmw !== '—' ? (toNum(mmw) * vScale) : '—';
  const bma = mma !== '—' ? (toNum(mma) * vScale) : '—';
  const bmsf = msf !== '—' ? (toNum(msf) * vScale) : '—';
  const bmtot = mtot !== '—' ? (toNum(mtot) * vScale) : '—';

  const isUHPC = record.category === 'uhpc' || record.category === 'uhpc_trial';
  
  let table1Head = '';
  let table1Body = '';
  if (!isUHPC) {
    table1Head = `<tr><th>类型</th><th>强度<br>等级</th><th>配制<br>强度<br>/MPa</th><th>胶凝总<br>量/kg</th><th>水泥<br>掺量/%</th><th>粉煤灰<br>掺量/%</th><th>矿粉<br>掺量/%</th><th>微珠<br>掺量/%</th><th>硅灰<br>掺量/%</th><th>水胶比</th><th>砂率<br>/%</th><th>外加剂<br>掺量/%</th></tr>`;
    table1Body = `<tr>
      <td align="center">HPC</td>
      <td align="center">${strengthGrade === '—' ? 'C80' : strengthGrade}</td>
      <td align="center">${fmtVal(designStrength,1)}</td>
      <td align="center">${fmtVal(totalBinder,1)}</td>
      <td align="center">${fmtVal(cementPct,1)}</td>
      <td align="center">${fmtVal(p1,1)}</td>
      <td align="center">${fmtVal(p2,1)}</td>
      <td align="center">${fmtVal(p3,1)}</td>
      <td align="center">${fmtVal(p4,1)}</td>
      <td align="center">${fmtVal(wb,3)}</td>
      <td align="center">${fmtVal(sandR,1)}</td>
      <td align="center">${fmtVal(admix,2)}</td>
    </tr>`;
  } else {
    table1Head = `<tr><th>类型</th><th>强度<br>等级</th><th>配制<br>强度<br>/MPa</th><th>胶凝总<br>量/kg</th><th>水泥<br>掺量/%</th><th>粉煤灰<br>掺量/%</th><th>微珠<br>掺量/%</th><th>硅灰<br>掺量/%</th><th>钢纤维<br>掺量/%</th><th>砂胶比</th><th>外加剂<br>掺量/%</th></tr>`;
    table1Body = `<tr>
      <td align="center">UHPC</td>
      <td align="center">${strengthGrade === '—' ? 'C130' : strengthGrade}</td>
      <td align="center">${fmtVal(designStrength,1)}</td>
      <td align="center">${fmtVal(totalBinder,1)}</td>
      <td align="center">${String(cementPct) !== '—' ? fmtVal(cementPct,1) : '—'}</td>
      <td align="center">${fmtVal(p1,1)}</td>
      <td align="center">${fmtVal(p3,1)}</td>
      <td align="center">${fmtVal(p4,1)}</td>
      <td align="center">${fmtVal(sf_vol,1)}</td>
      <td align="center">${fmtVal(sb,2)}</td>
      <td align="center">${fmtVal(admix,2)}</td>
    </tr>`;
  }

  let table2Head = '';
  let table2Body1 = '';
  let table2Body2 = '';
  if (!isUHPC) {
    table2Head = `<tr><th>状态</th><th>水泥</th><th>粉煤灰</th><th>矿粉</th><th>微珠</th><th>硅灰</th><th>粗骨料</th><th>细骨料</th><th>水</th><th>外加剂</th><th>合计</th></tr>`;
    table2Body1 = `<tr><td align="center">每方用量(kg)</td><td align="center">${fmtVal(mmc)}</td><td align="center">${fmtVal(mm1)}</td><td align="center">${fmtVal(mm2)}</td><td align="center">${fmtVal(mm3)}</td><td align="center">${fmtVal(mm4)}</td><td align="center">${fmtVal(mmg)}</td><td align="center">${fmtVal(mms)}</td><td align="center">${fmtVal(mmw)}</td><td align="center">${fmtVal(mma)}</td><td align="center">${fmtVal(mtot)}</td></tr>`;
    table2Body2 = `<tr><td align="center">试拌用量(${vBatch}L)</td><td align="center">${fmtVal(bmc)}</td><td align="center">${fmtVal(bm1)}</td><td align="center">${fmtVal(bm2)}</td><td align="center">${fmtVal(bm3)}</td><td align="center">${fmtVal(bm4)}</td><td align="center">${fmtVal(bmg)}</td><td align="center">${fmtVal(bms)}</td><td align="center">${fmtVal(bmw)}</td><td align="center">${fmtVal(bma)}</td><td align="center">${fmtVal(bmtot)}</td></tr>`;
  } else {
    table2Head = `<tr><th>状态</th><th>水泥</th><th>粉煤灰</th><th>微珠</th><th>硅灰</th><th>细骨料(砂)</th><th>钢纤维</th><th>水</th><th>外加剂</th><th>合计</th></tr>`;
    table2Body1 = `<tr><td align="center">每方用量(kg)</td><td align="center">${fmtVal(mmc)}</td><td align="center">${fmtVal(mm1)}</td><td align="center">${fmtVal(mm3)}</td><td align="center">${fmtVal(mm4)}</td><td align="center">${fmtVal(mms)}</td><td align="center">${fmtVal(msf)}</td><td align="center">${fmtVal(mmw)}</td><td align="center">${fmtVal(mma)}</td><td align="center">${fmtVal(mtot)}</td></tr>`;
    table2Body2 = `<tr><td align="center">试拌用量(${vBatch}L)</td><td align="center">${fmtVal(bmc)}</td><td align="center">${fmtVal(bm1)}</td><td align="center">${fmtVal(bm3)}</td><td align="center">${fmtVal(bm4)}</td><td align="center">${fmtVal(bms)}</td><td align="center">${fmtVal(bmsf)}</td><td align="center">${fmtVal(bmw)}</td><td align="center">${fmtVal(bma)}</td><td align="center">${fmtVal(bmtot)}</td></tr>`;
  }

  const printTimeStr = new Date().toLocaleString('zh-CN');

  

const html = `<!DOCTYPE html><html lang="zh-CN">
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
  <div class="section-title">二、 配合比及相关记录</div>
  <b>配合比关键参数</b>
  <table>
    <thead>${table1Head}</thead>
    <tbody>${table1Body}</tbody>
  </table>
  <br/>
  <b>最终配合比</b>
  <table>
    <thead>${table2Head}</thead>
    <tbody>${table2Body1}
${table2Body2}</tbody>
  </table>
  <div class="section-title">三、 混凝土性能</div>
  <table>
    <tbody>
      <tr><td class="kv-key">28d抗压强度 <span class="unit">[MPa]</span></td><td class="kv-val">${evalStrength || '—'}</td></tr>
      <tr><td class="kv-key">实测坍落度 <span class="unit">[mm]</span></td><td class="kv-val">${evalSlump || '—'}</td></tr>
      <tr><td class="kv-key">实测扩展度 <span class="unit">[mm]</span></td><td class="kv-val">${evalSpread || '—'}</td></tr>
      <tr><td class="kv-key">工作性及表现</td><td class="kv-val">${workDesc || '—'}</td></tr>
    </tbody>
  </table>
  <div class="footer">本记录由 中国中车风电混塔用混凝土配合比设计系统 自动生成 · 打印时间：${printTimeStr}</div>
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
onMounted(fetchProjects)
</script>

<template>
  <div class="report-layout">
    <!-- ── Left: Project list ─────────────────────────── -->
    <div class="report-left">
      <div class="cs-section" style="height: 100%">
        <div class="cs-section-head">
          <el-icon><Folder /></el-icon>
          项目列表
        </div>
        <div class="cs-section-body report-left-body">
          <el-input
            v-model="projectSearch"
            placeholder="搜索项目名称..."
            clearable
            @input="fetchProjects"
            style="margin-bottom: 12px"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>

          <div v-if="loadingProjects" class="project-loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            加载中...
          </div>
          <div v-else-if="projects.length === 0" class="project-empty">
            <el-empty description="暂无项目" :image-size="60" />
          </div>
          <div v-else class="project-list">
            <div
              v-for="proj in projects"
              :key="proj.id"
              class="project-item"
              :class="{ 'project-item--active': selectedProject?.id === proj.id }"
              @click="selectProject(proj)"
            >
              <div class="project-item__name">{{ proj.project_name }}</div>
              <div class="project-item__meta">
                <span>{{ proj.project_code }}</span>
                <el-tag size="small" type="info" style="margin-left: 6px">{{ proj.record_count }} 条记录</el-tag>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Right: Records ────────────────────────────── -->
    <div class="report-right">
      <!-- No project selected -->
      <div v-if="!selectedProject" class="report-empty">
        <el-empty description="请在左侧选择一个项目">
          <template #image>
            <el-icon style="font-size: 64px; color: #c0cfeb"><Document /></el-icon>
          </template>
        </el-empty>
      </div>

      <template v-else>
        <!-- Project header card -->
        <div class="cs-section">
          <div class="cs-section-head">
            <el-icon><FolderOpened /></el-icon>
            {{ selectedProject.project_name }}
          </div>
          <div class="cs-section-body">
            <el-descriptions :column="3" size="small" border>
              <el-descriptions-item label="项目编号">{{ selectedProject.project_code }}</el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ fmtDate(selectedProject.created_at) }}</el-descriptions-item>
              <el-descriptions-item label="记录数量">{{ selectedProject.record_count }} 条</el-descriptions-item>
              <el-descriptions-item v-if="selectedProject.requirements" label="需求说明" :span="3">
                {{ selectedProject.requirements }}
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </div>

        <!-- Records table card -->
        <div class="cs-section">
          <div class="cs-section-head">
            <el-icon><Document /></el-icon>
            配合比记录
            <span class="record-count-badge">共 {{ records.length }} 条</span>
          </div>
          <div class="cs-section-body report-records-body">
            <div v-if="loadingRecords" style="text-align:center; padding: 30px">
              <el-icon class="is-loading" :size="24"><Loading /></el-icon>
            </div>
            <el-empty v-else-if="records.length === 0" description="该项目暂无配合比记录" />
            <RecordTable
              :records="records"
              :loading="loadingRecords"
              border
            >
              <template #actions="{ row }">
                <el-tooltip content="导出报告" :show-after="300">
                  <el-button size="small" text type="primary" @click="exportReport(row)">
                    <el-icon><Printer /></el-icon>
                  </el-button>
                </el-tooltip>
              </template>
            </RecordTable>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.report-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 16px;
  align-items: start;
  height: calc(100vh - 120px);
}

.report-left {
  height: 100%;
}

.report-left-body {
  display: flex;
  flex-direction: column;
  height: calc(100% - 44px);
  overflow: hidden;
}

.project-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #9ca3af;
  font-size: 13px;
  padding: 20px;
  justify-content: center;
}

.project-empty {
  padding: 20px 0;
}

.project-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.project-item {
  padding: 10px 14px;
  border-radius: 8px;
  border: 1px solid #e8eff8;
  cursor: pointer;
  transition: all 0.15s;
  background: #fff;
}

.project-item:hover {
  border-color: #2a5298;
  background: #f0f5ff;
}

.project-item--active {
  border-color: #1e3c72;
  background: linear-gradient(135deg, #eef3ff, #dce8ff);
}

.project-item__name {
  font-size: 13px;
  font-weight: 700;
  color: #1e3c72;
  margin-bottom: 4px;
}

.project-item__meta {
  display: flex;
  align-items: center;
  font-size: 11px;
  color: #9ca3af;
}

.report-right {
  min-width: 0;
  overflow: hidden;
  min-height: 300px;
}

.report-records-body {
  overflow: hidden;
}

.report-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  border: 1px solid #dbe5f1;
  border-radius: 12px;
  background: #fff;
}

.record-count-badge {
  margin-left: 8px;
  font-size: 12px;
  font-weight: 400;
  color: #9ca3af;
  background: #f0f4fa;
  padding: 2px 8px;
  border-radius: 999px;
}
</style>
