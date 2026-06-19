<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteRecord, formatRecordNumber, type RecordItem } from '../api/records'
import { listProjectRecords, listProjects } from '../api/projects'
import type { Project } from '../api/projects'
import { exportRecord, downloadBlob } from '../api/exchange'
import ImportDialog from '../components/ImportDialog.vue'
import UhpcSidebarSummary from '../components/uhpc/UhpcSidebarSummary.vue'
import UhpcTabBinderRatios from '../components/uhpc/UhpcTabBinderRatios.vue'
import UhpcTabSandBinder from '../components/uhpc/UhpcTabSandBinder.vue'
import UhpcTabSteelFiber from '../components/uhpc/UhpcTabSteelFiber.vue'
import UhpcTabWaterBinder from '../components/uhpc/UhpcTabWaterBinder.vue'
import { useUhpcStore } from '../stores/uhpcStore'
import { debounce } from '../utils/debounce'

type UhpcTab = 'wb' | 'sand' | 'fiber' | 'binder'

const store = useUhpcStore()
const { calculationDeps, hasRequiredInputs } = storeToRefs(store)
const route = useRoute()
const router = useRouter()
const activeTab = ref<UhpcTab>('wb')

const tabOrder: UhpcTab[] = ['wb', 'sand', 'fiber', 'binder']

function parseProjectId(value: unknown): number | null {
  const raw = Array.isArray(value) ? value[0] : value
  const projectId = Number(raw)
  return Number.isInteger(projectId) && projectId > 0 ? projectId : null
}

function parseNewFlag(value: unknown): boolean {
  const raw = Array.isArray(value) ? value[0] : value
  return raw === '1' || raw === 'true'
}

const projectList = ref<Project[]>([])
const projectsLoading = ref(false)
const selectedProjectId = computed<number | null>({
  get: () => store.uhpcSelectedProjectId,
  set: (value) => {
    store.setUhpcProjectState(value, store.uhpcShowCalculator)
  },
})
const projectRecords = ref<RecordItem[]>([])
const recordsLoading = ref(false)
const projectRecordsPage = ref(1)
const projectRecordsPageSize = ref(5)
const showCalculator = computed<boolean>({
  get: () => store.uhpcShowCalculator,
  set: (value) => {
    store.setUhpcProjectState(store.uhpcSelectedProjectId, value)
  },
})
// ── 导入导出 ──
const importDialogVisible = ref(false)
const exportingId = ref<number | null>(null)

const showProjectSelect = computed(() => !showCalculator.value)
const hasSelectedProject = computed(() => selectedProjectId.value !== null)
const currentProjectName = computed(
  () => projectList.value.find((project) => project.id === selectedProjectId.value)?.project_name || '',
)
const projectRecordsEmptyDescription = computed(() => (
  hasSelectedProject.value
    ? '当前项目暂无超高性能混凝土配比记录。'
    : '请先选择项目，再查看该项目下的配比记录。'
))
const pagedProjectRecords = computed(() => {
  const start = (projectRecordsPage.value - 1) * projectRecordsPageSize.value
  return projectRecords.value.slice(start, start + projectRecordsPageSize.value)
})

const debouncedCalc = debounce(() => {
  void store.calcMix()
}, 500)

watch(calculationDeps, () => {
  if (!hasRequiredInputs.value) {
    store.clearCalculatedState()
    return
  }

  debouncedCalc()
}, { immediate: true })

onBeforeUnmount(() => {
  debouncedCalc.cancel()
})

async function loadProjects() {
  projectsLoading.value = true
  try {
    const result = await listProjects('', 1, 100)
    projectList.value = result.items
  } catch {
    projectList.value = []
  } finally {
    projectsLoading.value = false
  }
}

function clampProjectRecordPage() {
  const maxPage = Math.max(1, Math.ceil(projectRecords.value.length / projectRecordsPageSize.value))
  if (projectRecordsPage.value > maxPage) {
    projectRecordsPage.value = maxPage
  }
}

async function loadProjectRecords() {
  if (!selectedProjectId.value) {
    projectRecords.value = []
    projectRecordsPage.value = 1
    return
  }

  recordsLoading.value = true
  try {
    const records = await listProjectRecords(selectedProjectId.value)
    projectRecords.value = records.filter((record) => record.category === 'uhpc')
    clampProjectRecordPage()
  } catch {
    projectRecords.value = []
    projectRecordsPage.value = 1
  } finally {
    recordsLoading.value = false
  }
}

function openCalculatorForNewRecord() {
  if (!selectedProjectId.value) return
  store.resetAll()
  store.setCurrentRecord(null, '', selectedProjectId.value)
  activeTab.value = 'wb'
  showCalculator.value = true
}

async function selectProject(projectId: number) {
  const currentRouteProjectId = parseProjectId(route.query.project_id)
  selectedProjectId.value = projectId

  if (projectId === currentRouteProjectId) {
    projectRecordsPage.value = 1
    await loadProjectRecords()
    return
  }

  store.resetAll()
  activeTab.value = 'wb'
  showCalculator.value = false
  projectRecordsPage.value = 1
  await router.replace({ query: { project_id: projectId } })
}

function loadRecord(record: RecordItem) {
  store.applyRecordData(record)
  activeTab.value = 'wb'
  showCalculator.value = true
  ElMessage.success('UHPC 配比记录已载入')
}

async function handleDeleteRecord(record: RecordItem) {
  try {
    await ElMessageBox.confirm(`确认删除配比记录「${record.name}」？删除后会进入回收站，可恢复或彻底删除。`, '删除确认', {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteRecord(record.id)
    if (store.currentRecordId === record.id) {
      store.resetAll()
      store.setCurrentRecord(null, '', selectedProjectId.value)
      activeTab.value = 'wb'
      showCalculator.value = false
    }
    await loadProjectRecords()
    ElMessage.success('已移入回收站')
  } catch {
    // Ignore cancelled deletion.
  }
}

async function changeProject() {
  store.resetAll()
  activeTab.value = 'wb'
  projectRecords.value = []
  projectRecordsPage.value = 1
  store.clearUhpcProjectState()
  await router.replace({ query: {} })
}

async function syncRouteState() {
  const routeProjectId = parseProjectId(route.query.project_id)
  const currentProjectId = selectedProjectId.value
  const nextProjectId = routeProjectId ?? currentProjectId

  if (routeProjectId !== null && routeProjectId !== currentProjectId) {
    selectedProjectId.value = routeProjectId
    projectRecordsPage.value = 1
    if (store.currentRecordProjectId !== routeProjectId) {
      showCalculator.value = false
    }
  }

  if (!nextProjectId) {
    projectRecords.value = []
    return
  }

  if (selectedProjectId.value !== nextProjectId) {
    selectedProjectId.value = nextProjectId
  }

  await loadProjectRecords()

  if (parseNewFlag(route.query.new)) {
    openCalculatorForNewRecord()
    await router.replace({ query: { project_id: nextProjectId } })
    return
  }

  if (!showCalculator.value && store.currentRecordProjectId === nextProjectId && store.currentRecordId !== null) {
    showCalculator.value = true
  }
}

watch(() => [route.query.project_id, route.query.new] as const, () => {
  void syncRouteState()
}, { immediate: true })

onMounted(loadProjects)

function goNext() {
  const index = tabOrder.indexOf(activeTab.value)
  if (index < tabOrder.length - 1) {
    activeTab.value = tabOrder[index + 1]
  }
}

async function handleReset() {
  await ElMessageBox.confirm('确认重置当前 UHPC 计算页的全部数据？', '重置确认', {
    confirmButtonText: '确认重置',
    cancelButtonText: '取消',
    type: 'warning',
  })

  store.resetAll()
  store.setCurrentRecord(null, '', selectedProjectId.value)
  activeTab.value = 'wb'
}

// ── 导入导出 ──
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

function handleImportLoad(data: Record<string, unknown>, _category: string) {
  store.importFromExcel(data)
  if (selectedProjectId.value) {
    store.setCurrentRecord(null, (data.record_name as string) || '', selectedProjectId.value)
  }
  activeTab.value = 'wb'
  showCalculator.value = true
  ElMessage.success('导入成功，参数已载入计算界面')
}
</script>

<template>
  <div class="calc-view">
    <div class="calc-main">
      <el-card v-if="showProjectSelect" style="margin-bottom: 16px">
        <template #header>
          <span class="section-header">
            <el-icon><Folder /></el-icon>
            选择项目
          </span>
        </template>
        <p class="section-note">请先选择所属项目，再进行 UHPC 配比计算。配比记录会自动关联到当前项目。</p>
        <el-select
          v-model="selectedProjectId"
          placeholder="请选择项目"
          filterable
          style="width: 100%"
          :loading="projectsLoading"
          @change="selectProject"
        >
          <el-option
            v-for="project in projectList"
            :key="project.id"
            :label="`${project.project_code} - ${project.project_name}`"
            :value="project.id"
          />
        </el-select>
      </el-card>

      <el-card v-if="showProjectSelect" style="margin-bottom: 16px">
        <template #header>
          <div class="record-header">
            <span class="record-header__title">
              {{ hasSelectedProject ? `当前项目配比记录：${currentProjectName}` : '当前项目配比记录' }}
            </span>
            <el-button type="primary" size="small" :disabled="!hasSelectedProject" @click="openCalculatorForNewRecord">
              <el-icon><Plus /></el-icon>
              新建配比记录
            </el-button>
            <el-button size="small" :disabled="!hasSelectedProject" @click="importDialogVisible = true">
              <el-icon><Upload /></el-icon>
              导入配比
            </el-button>
          </div>
        </template>

        <el-table v-if="projectRecords.length" :data="pagedProjectRecords" stripe size="small" v-loading="recordsLoading">
          <el-table-column prop="name" label="名称" min-width="180" />
          <el-table-column prop="wb" label="W/B" width="100">
            <template #default="{ row }">
              {{ formatRecordNumber(row, 'wb', 3) }}
            </template>
          </el-table-column>
          <el-table-column prop="mb" label="胶材" width="90">
            <template #default="{ row }">
              {{ formatRecordNumber(row, 'mb', 1) }}
            </template>
          </el-table-column>
          <el-table-column prop="total_mass" label="合计" width="90">
            <template #default="{ row }">
              {{ formatRecordNumber(row, 'total_mass', 0) }}
            </template>
          </el-table-column>
          <el-table-column prop="created_by" label="创建人" width="100" />
          <el-table-column prop="created_at" label="时间" width="170" />
          <el-table-column label="操作" width="130" fixed="right">
            <template #default="{ row }">
              <el-button size="small" text type="primary" @click="loadRecord(row)">载入</el-button>
              <el-button size="small" text type="danger" @click="handleDeleteRecord(row)">删除</el-button>
              <el-button
                size="small"
                text
                type="success"
                :loading="exportingId === row.id"
                @click="handleExportRecord(row)"
              >
                导出
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-else v-loading="recordsLoading" :description="projectRecordsEmptyDescription" :image-size="80" />

        <div v-if="projectRecords.length" class="pagination-wrap">
          <el-pagination
            v-model:current-page="projectRecordsPage"
            v-model:page-size="projectRecordsPageSize"
            :total="projectRecords.length"
            :page-sizes="[5, 10, 20]"
            layout="total, sizes, prev, pager, next"
            background
          />
        </div>
      </el-card>

      <template v-if="!showProjectSelect">
        <div class="current-project-bar">
          <span class="current-project-bar__label">
            <el-icon><Folder /></el-icon>
            当前项目：<strong>{{ currentProjectName }}</strong>
          </span>
          <el-button size="small" text type="primary" @click="changeProject">更换项目</el-button>
        </div>

        <el-card :body-style="{ padding: 0 }" class="calc-card">
          <template #header>
            <div class="card-header">
              <div class="card-header__left">
                <span class="header-badge">UHPC Calc</span>
                <div>
                  <div class="header-title">超高性能混凝土配合比计算</div>
                  <div class="header-sub">{{ currentProjectName }}</div>
                </div>
              </div>
              <el-button type="danger" plain size="small" @click="handleReset">
                <el-icon><RefreshLeft /></el-icon>
                重置
              </el-button>
            </div>
          </template>

          <el-tabs v-model="activeTab" type="card" class="calc-tabs">
            <el-tab-pane label="水胶比" name="wb">
              <UhpcTabWaterBinder @next-step="goNext" />
            </el-tab-pane>

            <el-tab-pane label="砂胶比" name="sand">
              <UhpcTabSandBinder @next-step="goNext" />
            </el-tab-pane>

            <el-tab-pane label="钢纤维用量" name="fiber">
              <UhpcTabSteelFiber @next-step="goNext" />
            </el-tab-pane>

            <el-tab-pane label="胶凝材料比例" name="binder">
              <UhpcTabBinderRatios />
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </template>
    </div>

    <UhpcSidebarSummary v-if="showCalculator" />

    <!-- 导入对话框 -->
    <ImportDialog
      v-model:visible="importDialogVisible"
      :project-id="selectedProjectId"
      @load="handleImportLoad"
    />
  </div>
</template>

<style scoped>
.calc-view {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.calc-main {
  flex: 1;
  min-width: 0;
}

.calc-card {
  border-radius: 16px;
  border: 1px solid #dbe5f1;
}

.section-header {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #1e3c72;
  font-weight: 700;
}

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
  flex-shrink: 0;
}

.card-header__left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-title {
  font-size: 16px;
  font-weight: 800;
  color: #1e3c72;
}

.header-sub {
  font-size: 12px;
  color: #7b8794;
  margin-top: 2px;
}

.section-header {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #1e3c72;
  font-weight: 700;
}

.section-note {
  margin: 0 0 12px;
  color: #7b8794;
  font-size: 13px;
}

.record-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.record-header__title {
  color: #1e3c72;
  font-size: 13px;
  font-weight: 700;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.current-project-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.current-project-bar__label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #606266;
  font-size: 13px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #1e3c72;
  font-size: 15px;
  font-weight: 700;
}

.card-header__title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.calc-tabs :deep(.el-tabs__header) {
  background: #f8faff;
  border-bottom: 1px solid #eef3fb;
  padding: 0 16px;
  margin: 0;
}
.calc-tabs :deep(.el-tabs__item) {
  font-size: 14px;
  font-weight: 600;
  color: #7b8794;
}
.calc-tabs :deep(.el-tabs__item.is-active) {
  color: #1e3c72;
  font-weight: 800;
}
.calc-tabs :deep(.el-tabs__content) {
  padding: 20px;
  min-height: 420px;
}

@media (max-width: 1200px) {
  .calc-view {
    flex-direction: column;
  }
}
</style>
