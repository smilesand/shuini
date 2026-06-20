<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listProjects, listProjectRecords, type Project } from '../api/projects'
import { type RecordItem } from '../api/records'
import { exportRecord, exportProject, downloadBlob } from '../api/exchange'
import RecordTable from '../components/RecordTable.vue'
import ImportDialog from '../components/ImportDialog.vue'
import ImportProjectDialog from '../components/ImportProjectDialog.vue'
import { computeGroupValue } from '../composables/useStrengthEval'
import { generateReportHtml } from '../utils/reportHtml'
import html2pdf from 'html2pdf.js'

const projects = ref<Project[]>([])
const loadingProjects = ref(false)
const selectedProject = ref<Project | null>(null)
const records = ref<RecordItem[]>([])
const loadingRecords = ref(false)
const projectSearch = ref('')
const importDialogVisible = ref(false)
const importProjectVisible = ref(false)
const exportingId = ref<number | null>(null)
const exportingProject = ref(false)

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

async function refreshRecords() {
  if (!selectedProject.value) return
  loadingRecords.value = true
  try {
    records.value = await listProjectRecords(selectedProject.value.id)
  } catch {
    ElMessage.error('刷新记录失败')
  } finally {
    loadingRecords.value = false
  }
}

async function handleExportRecord(record: RecordItem) {
  exportingId.value = record.id
  try {
    const blob = await exportRecord(record.id)
    downloadBlob(blob, `${record.name}_${new Date().toISOString().slice(0, 10)}.xlsx`)
    ElMessage.success('导出成功')
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '导出失败')
  } finally {
    exportingId.value = null
  }
}

async function handleExportProject() {
  if (!selectedProject.value) return
  exportingProject.value = true
  try {
    const blob = await exportProject(selectedProject.value.id)
    downloadBlob(blob, `${selectedProject.value.project_code}_${new Date().toISOString().slice(0, 10)}.xlsx`)
    ElMessage.success('项目导出成功')
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '导出失败')
  } finally {
    exportingProject.value = false
  }
}

function handleImportLoad(_data: Record<string, unknown>, _category: string) {
  ElMessage.success('导入成功')
  void refreshRecords()
}

function handleProjectImportSuccess() {
  ElMessage.success('项目导入成功')
  void fetchProjects()
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
  const project = selectedProject.value
  const data = record.record_data ?? {}

  // ── Strength groups ─────────────────────────────────────────
  const rawGroups = extractEval(record, 'strengthGroups')
  let strengthGroups: { id: string; values: (number | null)[] }[] = []
  if (Array.isArray(rawGroups)) {
    strengthGroups = (rawGroups as any[]).map((g: any) => ({
      id: String(g.id ?? ''),
      values: Array.isArray(g.values) ? g.values.slice(0, 3) : [null, null, null],
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

  const groupEvals = strengthGroups.map(g => computeGroupValue(g.values))
  const validGroupAvgs = groupEvals.filter(e => !e.invalid).map(e => e.value).filter((v): v is number => v !== null)
  const strengthOverallAvg = validGroupAvgs.length > 0 ? validGroupAvgs.reduce((s, v) => s + v, 0) / validGroupAvgs.length : null
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

  // Flatten the data object
  const flatData: Record<string, any> = {}
  function flattenObj(obj: any) {
    if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return
    for (const [k, v] of Object.entries(obj)) {
      if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
        flattenObj(v)
      } else {
        flatData[k] = v
      }
    }
  }
  flattenObj(data)

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

  // ── Strength pass/fail: 总体均值 ≥ 1.15×强度等级 且 组最小值 ≥ 0.95×强度等级
  const targetForEval = sTargetStr || flatData.fcu0 || flatData.designStrength || flatData.design_strength
  const strengthGradeNum = Number(flatData.fcuk || flatData.strengthGrade || flatData.strength_grade || NaN)

  if (strengthOverallAvg !== null && Number.isFinite(strengthGradeNum)) {
    const overallOk = strengthOverallAvg >= strengthGradeNum * 1.15
    const minThreshold = strengthGradeNum * 0.95
    const minGroupOk = strengthMinGroupAvg !== null ? strengthMinGroupAvg >= minThreshold : null
    strengthPass = overallOk && (minGroupOk !== false)
  }

  // Lab Mix
  const calc = record.record_data?.calculated as Record<string, unknown> | undefined
  const mix: Record<string, unknown> = (calc?.labMix || calc?.lab_mix || calc?.mixProportion || calc || flatData) as Record<string, unknown>
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
  const toNum = (v: unknown) => (typeof v === 'number' ? v : NaN)
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

  const isUHPC = record.category === 'uhpc' || record.category === 'uhpc_trial'

  const html = generateReportHtml({
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
    strengthGroups,
    groupEvals,
    strengthOverallAvg,
    strengthMinGroupAvg,
    strengthGradeNum,
    targetForEval,
  })

  const el = document.createElement('div')
  el.innerHTML = html
  html2pdf()
    .set({
      margin: [10, 10, 10, 10],
      filename: `${record.name}.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
    })
    .from(el)
    .save()
    .then(() => el.remove())
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
            <div class="project-actions">
              <el-button size="small" @click="importProjectVisible = true">
                <el-icon><Upload /></el-icon>
                导入项目
              </el-button>
              <el-button size="small" :loading="exportingProject" @click="handleExportProject">
                <el-icon><Download /></el-icon>
                导出项目
              </el-button>
            </div>
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
            <el-button
              size="small"
              style="margin-left: auto"
              @click="importDialogVisible = true"
            >
              <el-icon><Upload /></el-icon>
              导入配比
            </el-button>
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
                <el-tooltip content="导出PDF" :show-after="300">
                  <el-button size="small" text type="primary" @click="exportReport(row)">
                    <el-icon><Printer /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="导出Excel" :show-after="300">
                  <el-button
                    size="small"
                    text
                    type="success"
                    :loading="exportingId === row.id"
                    @click="handleExportRecord(row)"
                  >
                    <el-icon><Download /></el-icon>
                  </el-button>
                </el-tooltip>
              </template>
            </RecordTable>
          </div>
        </div>
      </template>
    </div>

    <!-- 导入对话框 -->
    <ImportDialog
      v-model:visible="importDialogVisible"
      :project-id="selectedProject?.id ?? null"
      @load="handleImportLoad"
    />

    <!-- 导入项目对话框 -->
    <ImportProjectDialog
      v-model:visible="importProjectVisible"
      @success="handleProjectImportSuccess"
    />
  </div>
</template>

<style scoped>
.report-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 20px;
  align-items: start;
  height: calc(100vh - 100px);
  padding: 4px;
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
  padding: 30px;
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
  padding-right: 2px;
}

.project-list::-webkit-scrollbar {
  width: 4px;
}

.project-list::-webkit-scrollbar-thumb {
  background: #cdd7e6;
  border-radius: 4px;
}

.project-item {
  padding: 12px 16px;
  border-radius: 10px;
  border: 1px solid #e8eff8;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #fff;
  position: relative;
}

.project-item:hover {
  border-color: #2a5298;
  background: #f4f8ff;
  transform: translateX(2px);
  box-shadow: 0 2px 8px rgba(42, 82, 152, 0.08);
}

.project-item--active {
  border-color: #1e3c72;
  background: linear-gradient(135deg, #eef3ff, #dce8ff);
  box-shadow: 0 2px 12px rgba(30, 60, 114, 0.1);
}

.project-item--active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  background: #1e3c72;
  border-radius: 0 2px 2px 0;
}

.project-item__name {
  font-size: 14px;
  font-weight: 700;
  color: #1e3c72;
  margin-bottom: 4px;
  line-height: 1.3;
}

.project-item__meta {
  display: flex;
  align-items: center;
  font-size: 11px;
  color: #9ca3af;
  gap: 4px;
}

.report-right {
  min-width: 0;
  overflow: hidden;
  min-height: 300px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.report-records-body {
  overflow: hidden;
}

.report-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  border: 2px dashed #dbe5f1;
  border-radius: 16px;
  background: #fafbfd;
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

.project-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

/* ── Shared section card style ─────────────────────── */
.cs-section {
  background: #fff;
  border-radius: 14px;
  border: 1px solid #e4ebf5;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.2s;
}

.cs-section:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.cs-section-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 20px;
  font-size: 14px;
  font-weight: 700;
  color: #1e3c72;
  background: linear-gradient(180deg, #f8fafd, #f0f4fa);
  border-bottom: 1px solid #e4ebf5;
}

.cs-section-body {
  padding: 16px 20px;
}
</style>
