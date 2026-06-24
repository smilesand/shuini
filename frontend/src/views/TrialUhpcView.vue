<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import UhpcSidebarSummary from '../components/uhpc/UhpcSidebarSummary.vue'
import { useUhpcStore, type UhpcMaterialMasses } from '../stores/uhpcStore'
import { saveRecord } from '../api/records'
import { getProject } from '../api/projects'
import { calcUhpcTrial } from '../calc'
import type { UhpcTrialRes, UhpcTrialMixRowRes } from '../api/calc'
import { useAutoSave } from '../composables/useAutoSave'
import { debounce } from '../utils/debounce'
import UhpcTrialWorkabilityTab from '../components/uhpc-trial/UhpcTrialWorkabilityTab.vue'
import UhpcTrialStrengthTab from '../components/uhpc-trial/UhpcTrialStrengthTab.vue'
import UhpcTrialCorrectionTab from '../components/uhpc-trial/UhpcTrialCorrectionTab.vue'
import { type StrengthGroup } from '../composables/useStrengthEval'
import '../style/calc-tabs.css'

const route = useRoute()
const router = useRouter()
const store = useUhpcStore()

// ─── Tab state ───────────────────────────────────────────────────
type TrialTab = 'workability' | 'strength' | 'correction'
const activeTab = ref<TrialTab>('workability')

// ─── Tab 1: adjustable parameters ────────────────────────────────
const adjustedSB = ref<number | null>(null)
const adjustedAlpha = ref<number | null>(null)

// ─── Tab 2: strength measurements ────────────────────────────────
const sWb0 = ref<number | null>(null)
const sWbPlus = ref<number | null>(null)
const sWbMinus = ref<number | null>(null)
const sSfPlus = ref<number | null>(null)
const sSfMinus = ref<number | null>(null)

// 变体外加剂调整量
const aWbPlus = ref<number | null>(null)
const aWbMinus = ref<number | null>(null)
const aSfPlus = ref<number | null>(null)
const aSfMinus = ref<number | null>(null)

// ─── Tab 3: correction ───────────────────────────────────────────
type CorrBase = 'trial' | 'wbRec' | 'sfRec'
const corrBase = ref<CorrBase>('trial')
const measuredDensity = ref<number | null>(null)

// ─── Workability Eval ──────────────────────────────────────────────
const strengthGroups = ref<StrengthGroup[]>(defaultUhpcStrengthGroups())
const evalSpread = ref<number | null>(null)
const evalWorkabilityDesc = ref<string>('')

// ─── Project context ────────────────────────────────────────────
function parseProjectId(value: unknown): number | null {
  const raw = Array.isArray(value) ? value[0] : value
  const projectId = Number(raw)
  return Number.isInteger(projectId) && projectId > 0 ? projectId : null
}

const currentProjectId = computed(() => (
  parseProjectId(route.query.project_id)
  ?? store.currentRecordProjectId
))

const projectName = ref('')
const currentProjectLabel = computed(() => {
  if (projectName.value) return projectName.value
  return currentProjectId.value !== null ? `项目 #${currentProjectId.value}` : '未关联项目'
})

const currentRecordLabel = computed(() => {
  if (store.currentRecordName.trim()) return store.currentRecordName
  return store.currentRecordId !== null ? `记录 #${store.currentRecordId}` : '未关联配比记录'
})

const canUpdateCurrentRecord = computed(() => (
  store.currentRecordId !== null
  && store.currentRecordProjectId === currentProjectId.value
  && store.currentRecordName.trim().length > 0
))

watch(currentProjectId, async (projectId) => {
  if (projectId === null) { projectName.value = ''; return }
  try {
    const project = await getProject(projectId)
    projectName.value = project.project_name
  } catch { projectName.value = '' }
}, { immediate: true })

// ─── Save state ─────────────────────────────────────────────────
const saveVisible = ref(false)
const saveName = ref('')
const saving = ref(false)

// 定时自动保存：仅在已保存过的试配记录上，将试配改动（含最终配合比快照）定时同步到服务端。
useAutoSave({
  resolve: () => {
    if (!store.hasResults) return null
    if (store.currentRecordId == null) return null
    if (!store.currentRecordName.trim()) return null
    const projectId = currentProjectId.value
    if (projectId == null || store.currentRecordProjectId !== projectId) return null
    const base = store.buildRecordPayload(
      store.currentRecordName,
      projectId,
      store.currentRecordId,
    )
    const snapshot = buildTrialSnapshot()
    return { ...base, record_data: { ...base.record_data, trial_data: snapshot } }
  },
  onSaved: (id, payload) => {
    store.markRecordSaved(id, store.currentRecordName, store.currentRecordProjectId)
    const rd = payload.record_data as Record<string, unknown> | undefined
    if (rd?.trial_data) store.setCurrentTrialData(rd.trial_data as object)
    if (rd?.design_data) store.setCurrentDesignData(rd.design_data as object)
  },
})

function buildTrialSnapshot() {
  return {
    adjustedSB: adjustedSB.value,
    adjustedAlpha: adjustedAlpha.value,
    sWb0: sWb0.value,
    sWbPlus: sWbPlus.value,
    sWbMinus: sWbMinus.value,
    sSfPlus: sSfPlus.value,
    sSfMinus: sSfMinus.value,
    aWbPlus: aWbPlus.value,
    aWbMinus: aWbMinus.value,
    aSfPlus: aSfPlus.value,
    aSfMinus: aSfMinus.value,
    measuredDensity: measuredDensity.value,
    corrBase: corrBase.value,
    strengthGroups: strengthGroups.value.map(g => ({ id: g.id, values: [...g.values] })),
    evalSpread: evalSpread.value,
    evalWorkabilityDesc: evalWorkabilityDesc.value,
    // 持久化“调整适配后最终的实验室配合比”，供配合比记录表格展示最终配合比。
    lab_mix: trialResult.value?.lab_mix ?? null,
  }
}

async function persistTrialRecord(name: string) {
  const recordName = name.trim()
  if (!recordName) { ElMessage.warning('请输入试配记录名称'); return }
  if (!store.hasResults) { ElMessage.warning('请先在超高性能混凝土配合比计算页完成参数计算'); return }
  if (currentProjectId.value === null) { ElMessage.warning('当前试配尚未关联项目，无法保存'); return }

  const snapshot = buildTrialSnapshot()
  const updatingExistingRecord = canUpdateCurrentRecord.value

  saving.value = true
  try {
    const basePayload = store.buildRecordPayload(
      recordName,
      currentProjectId.value,
      updatingExistingRecord ? store.currentRecordId : null,
    )
    const result = await saveRecord({
      ...basePayload,
      record_data: {
        ...(basePayload.record_data ?? {}),
        trial_data: snapshot,
      },
    })
    store.markRecordSaved(result.id, recordName, currentProjectId.value)
    store.setCurrentDesignData(snapshot)
    store.setCurrentTrialData(snapshot)
    saveVisible.value = false
    ElMessage.success(updatingExistingRecord ? '试配记录已更新' : '试配记录已保存')
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '试配记录保存失败')
  } finally {
    saving.value = false
  }
}

function handlePersistTrial() {
  if (canUpdateCurrentRecord.value) {
    void persistTrialRecord(store.currentRecordName)
    return
  }
  saveName.value = store.currentRecordName || `${currentProjectLabel.value}试配`
  saveVisible.value = true
}

// ─── Helpers: base store values ──────────────────────────────────
function defaultUhpcStrengthGroups(): StrengthGroup[] {
  let n = 1
  return Array.from({ length: 6 }, () => ({
    id: `G${String(n++).padStart(2, '0')}`,
    values: [null, null, null] as (number | null)[],
  }))
}

const wb = computed(() => store.waterBinderRatio ?? 0.19)
const sb = computed(() => store.sandBinderRatio ?? 1.2)
const alpha = computed(() => store.admixtureRatio ?? 1.8)
const sfMass = computed(() => store.materialMasses.steelFiber ?? 0)
const total = computed(() => store.materialMasses.total ?? store.assumedMixMass ?? 2500)
const cr = computed(() => store.binderMassRatios.corrected)
const designStr = computed(() =>
  store.designStrength ?? ((store.strengthGrade ?? 130) * 1.1)
)

// ─── Trial result from backend ───────────────────────────────────
const trialResult = ref<UhpcTrialRes | null>(null)
const trialLoading = ref(false)

function buildTrialRequest() {
  if (!store.hasResults) return null
  return {
    wb: wb.value,
    sb: sb.value,
    alpha: alpha.value,
    sf_mass: sfMass.value,
    total: total.value,
    cement_pct: cr.value.cement ?? 0,
    fly_ash_pct: cr.value.flyAsh ?? 0,
    micro_bead_pct: cr.value.microBead ?? 0,
    silica_fume_pct: cr.value.silicaFume ?? 0,
    design_strength: designStr.value,
    adjusted_sb: adjustedSB.value,
    adjusted_alpha: adjustedAlpha.value,
    s_wb_0: sWb0.value,
    s_wb_plus: sWbPlus.value,
    s_wb_minus: sWbMinus.value,
    s_sf_plus: sSfPlus.value,
    s_sf_minus: sSfMinus.value,
    a_wb_plus: aWbPlus.value,
    a_wb_minus: aWbMinus.value,
    a_sf_plus: aSfPlus.value,
    a_sf_minus: aSfMinus.value,
    corr_base: corrBase.value,
    measured_density: measuredDensity.value,
  }
}

const debouncedCalc = debounce(() => {
  const req = buildTrialRequest()
  if (!req) { trialResult.value = null; return }
  trialLoading.value = true
  try {
    // 改为前端引擎同步计算（src/calc），服务端仅用于数据持久化。
    trialResult.value = calcUhpcTrial(req)
  } catch {
    trialResult.value = null
  } finally {
    trialLoading.value = false
  }
}, 500)

watch(() => [
  store.hasResults, adjustedSB.value, adjustedAlpha.value,
  sWb0.value, sWbPlus.value, sWbMinus.value, sSfPlus.value, sSfMinus.value,
  aWbPlus.value, aWbMinus.value, aSfPlus.value, aSfMinus.value,
  corrBase.value, measuredDensity.value,
], () => { debouncedCalc() }, { immediate: true })

onBeforeUnmount(() => { debouncedCalc.cancel() })

// ─── Derived from trial result ───────────────────────────────────
type MixRow = UhpcTrialMixRowRes

const trialSB = computed(() => trialResult.value?.trial_sb ?? adjustedSB.value ?? sb.value)
const trialAlpha = computed(() => trialResult.value?.trial_alpha ?? adjustedAlpha.value ?? alpha.value)
const trialMix = computed<MixRow | null>(() => trialResult.value?.trial_mix ?? null)
const vWbPlus = computed<MixRow | null>(() => trialResult.value?.variant_wb_plus ?? null)
const vWbMinus = computed<MixRow | null>(() => trialResult.value?.variant_wb_minus ?? null)
const vSfPlus = computed<MixRow | null>(() => trialResult.value?.variant_sf_plus ?? null)
const vSfMinus = computed<MixRow | null>(() => trialResult.value?.variant_sf_minus ?? null)
const recWb = computed(() => trialResult.value?.rec_wb ?? null)
const recSf = computed(() => trialResult.value?.rec_sf ?? null)
const corrMix = computed<MixRow | null>(() => trialResult.value?.corr_mix ?? null)
const calcDensity = computed(() => trialResult.value?.calc_density ?? null)
const corrFactor = computed(() => trialResult.value?.corr_factor ?? null)
const needsCorr = computed(() => trialResult.value?.needs_corr ?? false)
const labMix = computed<MixRow | null>(() => trialResult.value?.lab_mix ?? null)

// 变体外加剂初始值同步（仅在用户未手动调整时同步后端值）
watch(vWbPlus, (m) => { if (m && aWbPlus.value === null) aWbPlus.value = m.admixture })
watch(vWbMinus, (m) => { if (m && aWbMinus.value === null) aWbMinus.value = m.admixture })
watch(vSfPlus, (m) => { if (m && aSfPlus.value === null) aSfPlus.value = m.admixture })
watch(vSfMinus, (m) => { if (m && aSfMinus.value === null) aSfMinus.value = m.admixture })

// ─── Display helpers ─────────────────────────────────────────────
const MAT_KEYS = ['cement', 'fly_ash', 'micro_bead', 'silica_fume', 'sand', 'steel_fiber', 'water', 'admixture'] as const
type MatKey = typeof MAT_KEYS[number]
const MAT_LABELS: Record<MatKey, string> = {
  cement: '水泥', fly_ash: '粉煤灰', micro_bead: '微珠', silica_fume: '硅灰',
  sand: '砂', steel_fiber: '钢纤维', water: '水', admixture: '外加剂',
}

function fmt(v: number | null | undefined, d = 1): string {
  return v != null ? v.toFixed(d) : '—'
}
function storeVal(k: MatKey): number | null {
  const map: Record<MatKey, keyof UhpcMaterialMasses> = {
    cement: 'cement', fly_ash: 'flyAsh', micro_bead: 'microBead', silica_fume: 'silicaFume',
    sand: 'sand', steel_fiber: 'steelFiber', water: 'water', admixture: 'admixture',
  }
  return store.materialMasses[map[k]] as number | null
}
function mixVal(m: MixRow | null, k: MatKey): number | null {
  if (!m) return null
  return m[k] ?? null
}

const isFinalTab = computed(() => activeTab.value === 'correction')
function handleNext() {
  if (activeTab.value === 'workability') activeTab.value = 'strength'
  else if (activeTab.value === 'strength') activeTab.value = 'correction'
}
function goToCalc() { void router.push('/calc/uhpc') }

// ─── Trial data restore ──────────────────────────────────────────
function isPlainObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function applyTrialSnapshot(snapshot: unknown) {
  if (!isPlainObject(snapshot)) return
  const s = snapshot
  if (typeof s.adjustedSB === 'number') adjustedSB.value = s.adjustedSB
  if (typeof s.adjustedAlpha === 'number') adjustedAlpha.value = s.adjustedAlpha
  if (typeof s.sWb0 === 'number') sWb0.value = s.sWb0
  if (typeof s.sWbPlus === 'number') sWbPlus.value = s.sWbPlus
  if (typeof s.sWbMinus === 'number') sWbMinus.value = s.sWbMinus
  if (typeof s.sSfPlus === 'number') sSfPlus.value = s.sSfPlus
  if (typeof s.sSfMinus === 'number') sSfMinus.value = s.sSfMinus
  if (typeof s.aWbPlus === 'number') aWbPlus.value = s.aWbPlus
  if (typeof s.aWbMinus === 'number') aWbMinus.value = s.aWbMinus
  if (typeof s.aSfPlus === 'number') aSfPlus.value = s.aSfPlus
  if (typeof s.aSfMinus === 'number') aSfMinus.value = s.aSfMinus
  if (typeof s.measuredDensity === 'number') measuredDensity.value = s.measuredDensity
  if (typeof s.corrBase === 'string' && ['trial', 'wbRec', 'sfRec'].includes(s.corrBase)) {
    corrBase.value = s.corrBase as CorrBase
  }
  if (Array.isArray(s.strengthGroups)) {
    strengthGroups.value = (s.strengthGroups as StrengthGroup[]).map(g => ({
      id: g.id,
      values: Array.isArray(g.values) ? g.values.slice(0, 3) : [null, null, null],
    }))
  } else if (typeof s.evalStrength28d === 'number') {
    // Backward compat
    strengthGroups.value[0].values[0] = s.evalStrength28d
  }
  if (typeof s.evalSpread === 'number') evalSpread.value = s.evalSpread
  if (typeof s.evalWorkabilityDesc === 'string') evalWorkabilityDesc.value = s.evalWorkabilityDesc
}

watch(() => [store.currentRecordId, store.currentTrialData] as const, ([, trialData]) => {
  if (isPlainObject(trialData)) {
    applyTrialSnapshot(trialData)
  }
}, { immediate: true })

// Variant list for Tab 2 (for v-for iteration)
const variants = computed(() => [
  { label: '水胶比 +0.01', tagCls: 'tag--wb', mix: vWbPlus.value, sRef: sWbPlus, aRef: aWbPlus },
  { label: '水胶比 −0.01', tagCls: 'tag--wb', mix: vWbMinus.value, sRef: sWbMinus, aRef: aWbMinus },
  { label: '硅灰用量 +5%', tagCls: 'tag--sf', mix: vSfPlus.value, sRef: sSfPlus, aRef: aSfPlus },
  { label: '硅灰用量 −5%', tagCls: 'tag--sf', mix: vSfMinus.value, sRef: sSfMinus, aRef: aSfMinus },
])
</script>

<template>
  <div class="trial-view">
    <!-- ─── Main card ─── -->
    <div class="trial-main">
      <el-card :body-style="{ padding: 0 }" class="trial-card" shadow="never">
        <!-- Card header -->
        <template #header>
          <div class="card-header">
            <div class="header-left">
              <span class="header-badge">UHPC Trial</span>
              <div>
                <div class="header-title">超高性能混凝土试配</div>
                <div class="header-meta">
                  <span class="header-meta-item">项目：{{ currentProjectLabel }}</span>
                  <span class="header-meta-item">配比记录：{{ currentRecordLabel }}</span>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- No data state -->
        <div v-if="!store.hasResults" class="no-data">
          <el-empty description="请先在超高性能混凝土配合比计算页完成参数计算">
            <el-button type="primary" @click="goToCalc">
              <el-icon><ArrowRight /></el-icon>
              前往配合比计算
            </el-button>
          </el-empty>
        </div>

        <template v-else>
          <el-tabs v-model="activeTab" type="card" class="trial-tabs">

            <!-- ══════════════ Tab 1: 工作性试验 ══════════════ -->
            <el-tab-pane label="工作性试验" name="workability">
              <div class="pane-wrap">
                <UhpcTrialWorkabilityTab
                  :store-val="(k: string) => storeVal(k as MatKey)"
                  :store-total="store.materialMasses.total"
                  :sb="sb"
                  :alpha="alpha"
                  :trial-mix="trialMix"
                  :adjusted-s-b="adjustedSB"
                  :adjusted-alpha="adjustedAlpha"
                  :mat-keys="MAT_KEYS"
                  :mat-labels="MAT_LABELS"
                  @update:adjusted-s-b="v => adjustedSB = v"
                  @update:adjusted-alpha="v => adjustedAlpha = v"
                />
              </div>
            </el-tab-pane>

            <!-- ══════════════ Tab 2: 强度试验 ══════════════ -->
            <el-tab-pane label="强度试验" name="strength">
              <div class="pane-wrap">
                <UhpcTrialStrengthTab
                  :wb="wb"
                  :design-str="designStr"
                  :strength-grade="store.strengthGrade"
                  :mat-keys="MAT_KEYS"
                  :mat-labels="MAT_LABELS"
                  :trial-mix="trialMix"
                  :s-wb-0="sWb0"
                  :variants="variants"
                  :v-sf-plus="vSfPlus"
                  :v-sf-minus="vSfMinus"
                  :s-wb-plus="sWbPlus"
                  :s-wb-minus="sWbMinus"
                  :s-sf-plus="sSfPlus"
                  :s-sf-minus="sSfMinus"
                  :rec-wb="recWb"
                  :rec-sf="recSf"
                  @update:s-wb-0="v => sWb0 = v"
                />
              </div>
            </el-tab-pane>

            <!-- ══════════════ Tab 3: 配合比校正与确定 ══════════════ -->
            <el-tab-pane label="配合比校正与确定" name="correction">
              <div class="pane-wrap">
                <UhpcTrialCorrectionTab
                  :corr-base="corrBase"
                  :rec-wb="recWb"
                  :rec-sf="recSf"
                  :mat-keys="MAT_KEYS"
                  :mat-labels="MAT_LABELS"
                  :corr-mix="corrMix"
                  :measured-density="measuredDensity"
                  :calc-density="calcDensity"
                  :corr-factor="corrFactor"
                  :needs-corr="needsCorr"
                  :lab-mix="labMix"
                  :design-str="designStr"
                  :strength-grade="store.strengthGrade"
                  :strength-groups="strengthGroups"
                  :eval-spread="evalSpread"
                  :eval-workability-desc="evalWorkabilityDesc"
                  @update:corr-base="v => corrBase = v"
                  @update:measured-density="v => measuredDensity = v"
                  @update:strength-groups="v => strengthGroups = v"
                  @update:eval-spread="v => evalSpread = v"
                  @update:eval-workability-desc="v => evalWorkabilityDesc = v"
                />
              </div>
            </el-tab-pane>
          </el-tabs>

          <!-- Footer navigation -->
          <div class="trial-footer">
            <el-button v-if="!isFinalTab" type="primary" :disabled="!store.hasResults" @click="handleNext">
              下一步
              <el-icon><ArrowRight /></el-icon>
            </el-button>
            <el-button v-else type="primary" :loading="saving" :disabled="!store.hasResults" @click="handlePersistTrial">
              保存配比记录
              <el-icon><FolderAdd /></el-icon>
            </el-button>
          </div>
        </template>
      </el-card>
    </div>

    <!-- ─── Sidebar ─── -->
    <div class="trial-sidebar">
      <UhpcSidebarSummary />
    </div>

    <!-- ─── Save dialog ─── -->
    <el-dialog v-model="saveVisible" title="保存超高性能配比记录" width="420px">
      <el-form label-width="96px">
        <el-form-item label="项目">
          <el-input :model-value="currentProjectLabel" disabled />
        </el-form-item>
        <el-form-item label="记录名称">
          <el-input v-model="saveName" placeholder="请输入试配记录名称" maxlength="100" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="saveVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="persistTrialRecord(saveName)">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* ── Layout ──────────────────────────────────────────────────── */
.trial-view {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 16px;
  align-items: start;
}

.trial-sidebar {
  position: sticky;
  top: 20px;
}

/* ── Card ─────────────────────────────────────────────────────── */
.trial-card {
  border-radius: 16px;
  border: 1px solid #dbe5f1;
}

/* ── Card header ──────────────────────────────────────────────── */
.card-header { display: flex; align-items: center; }

.header-badge {
  display: inline-block;
  padding: 4px 12px;
  background: linear-gradient(135deg, #1e3c72, #2a5298);
  color: #fff;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-right: 14px;
  flex-shrink: 0;
}

.header-title { font-size: 18px; font-weight: 800; color: #1e3c72; }

.header-meta {
  display: flex; flex-wrap: wrap; align-items: center; gap: 5px;
  font-size: 13px; color: #5b6472; margin-top: 4px;
}

.header-meta-item {
  display: inline-flex; align-items: center; min-height: 24px;
  padding: 0 10px; border-radius: 999px; background: #eef4ff;
  color: #1e3c72; font-size: 12px; font-weight: 700;
}

/* ── Tabs ─────────────────────────────────────────────────────── */
.trial-tabs :deep(.el-tabs__header) {
  background: #f8faff; border-bottom: 1px solid #eef3fb;
  margin: 0; padding: 0 16px;
}
.trial-tabs :deep(.el-tabs__item) { font-size: 14px; font-weight: 600; color: #7b8794; }
.trial-tabs :deep(.el-tabs__item.is-active) { color: #1e3c72; font-weight: 800; }
.trial-tabs :deep(.el-tabs__content) { overflow: visible; }

/* ── Pane body ────────────────────────────────────────────────── */
.pane { padding: 20px; }
.pane-wrap { padding: 20px; }

/* ── Footer ───────────────────────────────────────────────────── */
.trial-footer {
  display: flex; justify-content: flex-end; padding: 14px 20px;
  border-top: 1px solid #eef3fb; background: #f8faff;
  border-radius: 0 0 16px 16px;
}

/* ── No data ──────────────────────────────────────────────────── */
.no-data { padding: 60px 20px; }
</style>