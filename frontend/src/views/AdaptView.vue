<script setup lang="ts">
import { computed, onBeforeUnmount, provide, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import HpcTrialWorkabilityTab from '../components/hpc-trial/HpcTrialWorkabilityTab.vue'
import HpcTrialStrengthTab from '../components/hpc-trial/HpcTrialStrengthTab.vue'
import HpcTrialCorrectionTab from '../components/hpc-trial/HpcTrialCorrectionTab.vue'
import HpcTrialSummary from '../components/hpc-trial/HpcTrialSummary.vue'
import { saveRecord } from '../api/records'
import { getProject } from '../api/projects'
import { hpcTrialKey } from '../composables/context'
import { useHpcTrial, type HpcTrialTab } from '../composables/useHpcTrial'
import { useCalcStore } from '../stores/calcStore'
import { useAutoSave } from '../composables/useAutoSave'
import { debounce } from '../utils/debounce'
import '../components/hpc-trial/styles.css'

const route = useRoute()
const router = useRouter()
const store = useCalcStore()
const activeTab = ref<HpcTrialTab>('workability')
const trial = useHpcTrial()
const { hasData } = trial
const projectName = ref('')
const saveVisible = ref(false)
const saveName = ref('')
const saving = ref(false)

function parseProjectId(value: unknown): number | null {
  const raw = Array.isArray(value) ? value[0] : value
  const projectId = Number(raw)
  return Number.isInteger(projectId) && projectId > 0 ? projectId : null
}

const currentProjectId = computed(() => (
  parseProjectId(route.query.project_id)
  ?? store.currentRecordProjectId
  ?? store.hpcSelectedProjectId
))

const currentProjectLabel = computed(() => {
  if (projectName.value) {
    return projectName.value
  }

  return currentProjectId.value !== null ? `项目 #${currentProjectId.value}` : '未关联项目'
})

const currentRecordLabel = computed(() => {
  if (store.currentRecordName.trim()) {
    return store.currentRecordName
  }

  return store.currentRecordId !== null ? `记录 #${store.currentRecordId}` : '未关联配比记录'
})

const canUpdateCurrentRecord = computed(() => (
  store.currentRecordId !== null
  && store.currentRecordProjectId === currentProjectId.value
  && store.currentRecordName.trim().length > 0
))

const isFinalTab = computed(() => activeTab.value === 'correction')
const primaryButtonText = computed(() => (
  isFinalTab.value ? '保存配比记录' : '下一步'
))

// 与主计算页保持同一触发方式：任一相关输入变化后，经过节流防抖再向后端发起试配计算。
const debouncedCalc = debounce(() => {
  void trial.calcTrial()
}, 500)

provide(hpcTrialKey, trial)

// 定时自动保存：仅在已保存过的试配记录上，将试配改动（含试配快照）定时同步到服务端。
useAutoSave({
  resolve: () => {
    if (!trial.hasData.value) return null
    if (store.currentRecordId == null) return null
    if (!store.currentRecordName.trim()) return null
    const projectId = currentProjectId.value
    if (projectId == null || store.currentRecordProjectId !== projectId) return null
    const base = store.buildRecordPayload(
      'hpc',
      store.currentRecordName,
      projectId,
      store.currentRecordId,
    )
    const snapshot = trial.buildTrialSnapshot()
    return { ...base, record_data: { ...base.record_data, trial_data: snapshot } }
  },
  onSaved: (id, payload) => {
    store.markRecordSaved(id, store.currentRecordName, store.currentRecordProjectId)
    const trialData = (payload.record_data as Record<string, unknown> | undefined)?.trial_data
    if (trialData) {
      store.setCurrentTrialData(trialData as object)
    }
  },
})

watch(currentProjectId, async (projectId) => {
  if (projectId === null) {
    projectName.value = ''
    return
  }

  try {
    const project = await getProject(projectId)
    projectName.value = project.project_name
  } catch {
    projectName.value = ''
  }
}, { immediate: true })

watch(trial.calculationDeps, () => {
  if (!trial.hasData.value) {
    trial.clearCalculatedState()
    return
  }

  debouncedCalc()
}, { immediate: true })

onBeforeUnmount(() => {
  debouncedCalc.cancel()
})

async function handleReset() {
  await ElMessageBox.confirm('确认重置当前高性能试配页的全部实验数据？', '重置确认', {
    confirmButtonText: '确认重置',
    cancelButtonText: '取消',
    type: 'warning',
  })

  trial.resetTrial()
}

async function persistTrialRecord(name: string) {
  const recordName = name.trim()

  if (!recordName) {
    ElMessage.warning('请输入试配记录名称')
    return
  }

  if (!trial.hasData.value) {
    ElMessage.warning('请先在配比计算中形成有效的高性能混凝土基准配合比')
    return
  }

  if (currentProjectId.value === null) {
    ElMessage.warning('当前试配尚未关联项目，无法保存')
    return
  }

  const snapshot = trial.buildTrialSnapshot()
  const updatingExistingRecord = canUpdateCurrentRecord.value

  saving.value = true
  try {
    const basePayload = store.buildRecordPayload(
      'hpc',
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

function handlePrimaryAction() {
  if (activeTab.value === 'workability') {
    trial.applyWorkabilityToCorrection()
    activeTab.value = 'strength'
    return
  }

  if (activeTab.value === 'strength') {
    trial.applyWorkabilityToCorrection()
    if (trial.strengthRegression.value?.recommendWb != null) {
      trial.loadStrengthRecommendation()
    }
    activeTab.value = 'correction'
    return
  }

  handlePersistTrial()
}
</script>

<template>
  <div class="hpc-trial-view">
    <div class="hpc-trial-main">
      <el-card :body-style="{ padding: 0 }" class="hpc-trial-card">
        <template #header>
          <div class="card-header">
            <div class="hpc-trial-title">
              <span class="hpc-trial-pill">HPC Trial</span>
              <div>
                <div class="hpc-trial-heading">高性能试配</div>
                <div class="hpc-trial-meta">
                  <span class="hpc-trial-meta-item">项目：{{ currentProjectLabel }}</span>
                  <span class="hpc-trial-meta-item">配比记录：{{ currentRecordLabel }}</span>
                </div>
              </div>
            </div>

            <div class="hpc-trial-actions">
              <el-button type="danger" plain size="small" @click="handleReset">
                <el-icon><RefreshLeft /></el-icon>
                重置
              </el-button>
            </div>
          </div>
        </template>

        <div v-if="!hasData" class="no-data-state">
          <el-empty description="请先在高性能混凝土配合比计算页完成参数计算">
            <el-button type="primary" @click="router.push('/calc/hpc')">
              <el-icon><ArrowRight /></el-icon>
              前往配比计算
            </el-button>
          </el-empty>
        </div>

        <template v-else>
          <el-tabs v-model="activeTab" type="card" class="hpc-trial-tabs">
            <el-tab-pane label="工作性实验" name="workability">
              <HpcTrialWorkabilityTab />
            </el-tab-pane>

            <el-tab-pane label="强度实验" name="strength">
              <HpcTrialStrengthTab />
            </el-tab-pane>

            <el-tab-pane label="配合比校正与确认" name="correction">
              <HpcTrialCorrectionTab />
            </el-tab-pane>
          </el-tabs>

          <div class="hpc-trial-footer-actions">
            <el-button type="primary" :loading="saving" :disabled="!hasData" @click="handlePrimaryAction">
              {{ primaryButtonText }}
              <el-icon>
                <ArrowRight v-if="!isFinalTab" />
                <FolderAdd v-else />
              </el-icon>
            </el-button>
          </div>
        </template>
      </el-card>
    </div>

    <div class="hpc-trial-sidebar">
      <HpcTrialSummary :active-tab="activeTab" />
    </div>

    <el-dialog v-model="saveVisible" title="保存高性能配比记录" width="420px">
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
