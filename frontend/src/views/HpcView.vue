<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useCalcStore } from "../stores/calcStore";
import SidebarSummary from "../components/SidebarSummary.vue";
import TabWaterBinder from "../components/hpc/HpcTabWaterBinder.vue";
import TabSandRatio from "../components/hpc/HpcTabSandRatio.vue";
import TabAggregate from "../components/hpc/HpcTabAggregate.vue";
import TabBinder from "../components/hpc/HpcTabBinder.vue";
import TabWaterAdmix from "../components/hpc/HpcTabWaterAdmix.vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { deleteRecord, type RecordItem } from "../api/records";
import { listProjectRecords, listProjects } from "../api/projects";
import type { Project } from "../api/projects";
import ImportDialog from "../components/ImportDialog.vue";
import RecordTable from "../components/RecordTable.vue";
import { useAutoSave } from "../composables/useAutoSave";

const store = useCalcStore();
const route = useRoute();
const router = useRouter();
const activeTab = ref("wb");

// 定时自动保存：仅在已保存过的记录上，将主计算页改动定时同步到服务端。
useAutoSave({
  resolve: () => {
    if (store.currentRecordId == null) return null;
    if (!store.currentRecordName.trim()) return null;
    const projectId = store.currentRecordProjectId;
    if (projectId == null) return null;
    const base = store.buildRecordPayload(
      "hpc",
      store.currentRecordName,
      projectId,
      store.currentRecordId,
    );
    // 保留已存在的试配数据，避免主计算页自动保存覆盖掉试配快照。
    const record_data = store.currentTrialData
      ? { ...base.record_data, trial_data: store.currentTrialData }
      : base.record_data;
    return { ...base, record_data };
  },
  onSaved: (id) => {
    store.markRecordSaved(id, store.currentRecordName, store.currentRecordProjectId);
  },
});

const tabOrder = ["wb", "sand", "agg", "binder", "admix"] as const;

function parseProjectId(value: unknown): number | null {
  const raw = Array.isArray(value) ? value[0] : value;
  const projectId = Number(raw);
  return Number.isInteger(projectId) && projectId > 0 ? projectId : null;
}

function parseNewFlag(value: unknown): boolean {
  const raw = Array.isArray(value) ? value[0] : value;
  return raw === "1" || raw === "true";
}

// ── 项目选择 ──
const projectList = ref<Project[]>([]);
const projectsLoading = ref(false);
const selectedProjectId = computed<number | null>({
  get: () => store.hpcSelectedProjectId,
  set: (value) => {
    store.setHpcProjectState(value, store.hpcShowCalculator);
  },
});
const projectRecords = ref<RecordItem[]>([]);
const recordsLoading = ref(false);
const projectRecordsPage = ref(1);
const projectRecordsPageSize = ref(5);
const showCalculator = computed<boolean>({
  get: () => store.hpcShowCalculator,
  set: (value) => {
    store.setHpcProjectState(store.hpcSelectedProjectId, value);
  },
});
// ── 导入导出 ──
const importDialogVisible = ref(false);
const showProjectSelect = computed(() => !showCalculator.value);
const hasSelectedProject = computed(() => selectedProjectId.value !== null);
const currentProjectName = computed(
  () =>
    projectList.value.find((project) => project.id === selectedProjectId.value)
      ?.project_name || "",
);
const projectRecordsEmptyDescription = computed(() =>
  hasSelectedProject.value
    ? "当前项目暂无高性能混凝土配比记录。"
    : "请先选择项目，再查看该项目下的配比记录。",
);
const pagedProjectRecords = computed(() => {
  const start = (projectRecordsPage.value - 1) * projectRecordsPageSize.value;
  return projectRecords.value.slice(
    start,
    start + projectRecordsPageSize.value,
  );
});

// 加载可选项目列表
async function loadProjects() {
  projectsLoading.value = true;
  try {
    const res = await listProjects("", 1, 100);
    projectList.value = res.items;
  } catch {
    projectList.value = [];
  } finally {
    projectsLoading.value = false;
  }
}

function clampProjectRecordPage() {
  const maxPage = Math.max(
    1,
    Math.ceil(projectRecords.value.length / projectRecordsPageSize.value),
  );
  if (projectRecordsPage.value > maxPage) {
    projectRecordsPage.value = maxPage;
  }
}

async function loadProjectRecords() {
  if (!selectedProjectId.value) {
    projectRecords.value = [];
    projectRecordsPage.value = 1;
    return;
  }

  recordsLoading.value = true;
  try {
    const records = await listProjectRecords(selectedProjectId.value);
    projectRecords.value = records.filter(
      (record) => record.category === "hpc",
    );
    clampProjectRecordPage();
  } catch {
    projectRecords.value = [];
    projectRecordsPage.value = 1;
  } finally {
    recordsLoading.value = false;
  }
}

function openCalculatorForNewRecord() {
  if (!selectedProjectId.value) return;
  store.resetAll();
  store.setCurrentRecord(null, "", selectedProjectId.value);
  activeTab.value = "wb";
  showCalculator.value = true;
}

// 选择项目
async function selectProject(pid: number) {
  const currentRouteProjectId = parseProjectId(route.query.project_id);
  selectedProjectId.value = pid;

  if (pid === currentRouteProjectId) {
    projectRecordsPage.value = 1;
    await loadProjectRecords();
    return;
  }

  store.resetAll();
  activeTab.value = "wb";
  showCalculator.value = false;
  projectRecordsPage.value = 1;
  await router.replace({ query: { project_id: pid } });
}

async function loadRecord(record: RecordItem) {
  store.applyRecordData(record);
  activeTab.value = "wb";
  showCalculator.value = true;
  ElMessage.success("载入成功");
}

async function handleDeleteRecord(record: RecordItem) {
  try {
    await ElMessageBox.confirm(
      `确认删除配比记录「${record.name}」？删除后会进入回收站，可恢复或彻底删除。`,
      "删除确认",
      {
        confirmButtonText: "确认删除",
        cancelButtonText: "取消",
        type: "warning",
      },
    );
    await deleteRecord(record.id);
    if (store.currentRecordId === record.id) {
      store.resetAll();
      store.setCurrentRecord(null, "", selectedProjectId.value);
      activeTab.value = "wb";
      showCalculator.value = false;
    }
    await loadProjectRecords();
    ElMessage.success("已移入回收站");
  } catch {
    // Ignore cancelled deletion.
  }
}

async function changeProject() {
  store.resetAll();
  activeTab.value = "wb";
  projectRecords.value = [];
  projectRecordsPage.value = 1;
  store.clearHpcProjectState();
  await router.replace({ query: {} });
}

async function syncRouteState() {
  const routeProjectId = parseProjectId(route.query.project_id);
  const currentProjectId = selectedProjectId.value;
  const nextProjectId = routeProjectId ?? currentProjectId;

  if (routeProjectId !== null && routeProjectId !== currentProjectId) {
    selectedProjectId.value = routeProjectId;
    projectRecordsPage.value = 1;
    if (
      store.currentRecordProjectId !== routeProjectId
    ) {
      showCalculator.value = false;
    }
  }

  if (!nextProjectId) {
    projectRecords.value = [];
    return;
  }

  if (selectedProjectId.value !== nextProjectId) {
    selectedProjectId.value = nextProjectId;
  }

  await loadProjectRecords();

  if (parseNewFlag(route.query.new)) {
    openCalculatorForNewRecord();
    await router.replace({ query: { project_id: nextProjectId } });
    return;
  }

  if (
    !showCalculator.value &&
    store.currentRecordProjectId === nextProjectId &&
    (store.currentRecordId !== null || store.fcuk !== null)
  ) {
    showCalculator.value = true;
  }
}

watch(
  () => [route.query.project_id, route.query.new] as const,
  () => {
    void syncRouteState();
  },
  { immediate: true },
);

onMounted(loadProjects);

/** 跳转到下一个计算步骤 */
function goNext() {
  const idx = tabOrder.indexOf(activeTab.value as (typeof tabOrder)[number]);
  if (idx < tabOrder.length - 1) {
    activeTab.value = tabOrder[idx + 1];
  }
}

async function handleReset() {
  await ElMessageBox.confirm("确认重置所有计算数据？", "重置确认", {
    confirmButtonText: "确认重置",
    cancelButtonText: "取消",
    type: "warning",
  });
  store.resetAll();
  activeTab.value = "wb";
}

function handleImportLoad(data: Record<string, unknown>, _category: string) {
  store.importFromExcel(data);
  if (selectedProjectId.value) {
    store.setCurrentRecord(null, (data.record_name as string) || "", selectedProjectId.value);
  }
  activeTab.value = "wb";
  showCalculator.value = true;
  ElMessage.success("导入成功，参数已载入计算界面");
}
</script>

<template>
  <div class="calc-view">
    <!-- 主区域 -->
    <div class="calc-main">
      <!-- ── 项目选择（如未选择则先显示）── -->
      <el-card v-if="showProjectSelect" style="margin-bottom: 16px">
        <template #header>
          <span class="section-header">
            <el-icon><Folder /></el-icon> 选择项目
          </span>
        </template>
        <p class="section-note">
          请先选择所属项目，再进行配比计算。配比记录将自动关联到该项目下。
        </p>
        <el-select
          v-model="selectedProjectId"
          placeholder="请选择项目"
          filterable
          style="width: 100%"
          @change="selectProject"
          :loading="projectsLoading"
        >
          <el-option
            v-for="p in projectList"
            :key="p.id"
            :label="`${p.project_code} - ${p.project_name}`"
            :value="p.id"
          />
        </el-select>
      </el-card>

      <el-card v-if="showProjectSelect" style="margin-bottom: 16px">
        <template #header>
          <div class="record-header">
            <span class="record-header__title">
              {{ hasSelectedProject ? `当前项目配比记录：${currentProjectName}` : "当前项目配比记录" }}
            </span>
            <div class="record-header__actions">
              <el-button type="primary" size="small" :disabled="!hasSelectedProject" @click="openCalculatorForNewRecord">
                <el-icon><Plus /></el-icon>
                新建配比记录
              </el-button>
              <el-button size="small" :disabled="!hasSelectedProject" @click="importDialogVisible = true">
                <el-icon><Upload /></el-icon>
                导入配比
              </el-button>
            </div>
          </div>
        </template>

        <RecordTable
          :records="pagedProjectRecords"
          :loading="recordsLoading"
          :empty-description="projectRecordsEmptyDescription"
          hide-category
        >
          <template #actions="{ row }">
            <el-tooltip content="载入" :show-after="300">
              <el-button size="small" text type="primary" @click="loadRecord(row)">
                <el-icon><Right /></el-icon>
              </el-button>
            </el-tooltip>
            <el-tooltip content="删除" :show-after="300">
              <el-button size="small" text type="danger" @click="handleDeleteRecord(row)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </el-tooltip>
          </template>
        </RecordTable>

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

      <!-- ── 已选项目 + 配比记录 ── -->
      <template v-if="!showProjectSelect">
        <div class="current-project-bar">
          <span class="current-project-bar__label">
            <el-icon><Folder /></el-icon>
            当前项目：<strong>{{ currentProjectName }}</strong>
          </span>
          <el-button size="small" text type="primary" @click="changeProject">更换项目</el-button>
        </div>

        <!-- 计算卡片 -->
        <el-card :body-style="{ padding: 0 }" class="calc-card">
          <template #header>
            <div class="card-header">
              <div class="card-header__left">
                <span class="header-badge">HPC Calc</span>
                <div>
                  <div class="header-title">混凝土配合比计算</div>
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
              <TabWaterBinder @next-step="goNext" />
            </el-tab-pane>
            <el-tab-pane label="砂率选取" name="sand">
              <TabSandRatio @next-step="goNext" />
            </el-tab-pane>
            <el-tab-pane label="骨料用量" name="agg">
              <TabAggregate @next-step="goNext" />
            </el-tab-pane>
            <el-tab-pane label="胶凝材料" name="binder"
              ><TabBinder @next-step="goNext" />
            </el-tab-pane>
            <el-tab-pane label="水和外加剂" name="admix">
              <TabWaterAdmix @next-step="goNext" />
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </template>
    </div>

    <!-- 右侧汇总 -->
    <SidebarSummary v-if="showCalculator" />

    <!-- 导入对话框 -->
    <ImportDialog
      v-model:visible="importDialogVisible"
      :project-id="selectedProjectId"
      category="hpc"
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

.calc-tabs {
  --calc-field-width: 380px;
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

.record-header__actions {
  display: flex;
  align-items: center;
  gap: 8px;
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

.calc-placeholder :deep(.el-card__body) {
  min-height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 15px;
  font-weight: 700;
  color: #1e3c72;
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

.calc-tabs :deep(.el-row > .el-col) {
  flex: 0 0 var(--calc-field-width);
  max-width: var(--calc-field-width);
}

@media (max-width: 960px) {
  .calc-tabs :deep(.el-row > .el-col) {
    flex: 0 0 100%;
    max-width: 100%;
  }
}
</style>
