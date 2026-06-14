<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { deleteRecord, formatRecordNumber, listRecords, type RecordItem } from '../../api/records'
import { useUhpcStore } from '../../stores/uhpcStore'

const route = useRoute()
const store = useUhpcStore()

function parseProjectId(value: unknown): number | undefined {
  const raw = Array.isArray(value) ? value[0] : value
  const projectId = Number(raw)
  return Number.isInteger(projectId) && projectId > 0 ? projectId : undefined
}

const currentProjectId = computed(() => parseProjectId(route.query.project_id))
const historyTitle = computed(() => currentProjectId.value ? '当前项目 UHPC 历史记录' : 'UHPC 历史记录')
const historyEmptyDescription = computed(() => {
  if (historySearch.value) return '未找到匹配记录'
  if (currentProjectId.value) return '当前项目暂无超高性能混凝土配比记录'
  return '暂无超高性能混凝土配比记录'
})

const historyVisible = ref(false)
const historyItems = ref<RecordItem[]>([])
const historyLoading = ref(false)
const historyTotal = ref(0)
const historyPage = ref(1)
const historyPageSize = ref(10)
const historySearch = ref('')

function fmt(value: number | null, digits = 2): string {
  return value !== null ? value.toFixed(digits) : '—'
}

async function fetchHistory() {
  historyLoading.value = true
  try {
    const result = await listRecords({
      category: 'uhpc',
      project_id: currentProjectId.value,
      search: historySearch.value.trim(),
      page: historyPage.value,
      page_size: historyPageSize.value,
    })
    historyItems.value = result.items
    historyTotal.value = result.total
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '加载 UHPC 历史记录失败')
  } finally {
    historyLoading.value = false
  }
}

function openHistory() {
  historyVisible.value = true
  historySearch.value = ''
  historyPage.value = 1
  void fetchHistory()
}

function onHistorySearch() {
  historyPage.value = 1
  void fetchHistory()
}

function onHistoryPageChange(page: number) {
  historyPage.value = page
  void fetchHistory()
}

function onHistorySizeChange(size: number) {
  historyPageSize.value = size
  historyPage.value = 1
  void fetchHistory()
}

function applyRecord(record: RecordItem) {
  ElMessageBox.confirm(
    `确认载入 "${record.name}" 的 UHPC 配比数据？`,
    '载入配比记录',
    { confirmButtonText: '确认载入', cancelButtonText: '取消', type: 'info' },
  ).then(() => {
    store.applyRecordData(record)
    ElMessage.success('UHPC 历史记录已载入')
  }).catch(() => {})
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
    }
    ElMessage.success('已移入回收站')
    await fetchHistory()
  } catch {
    // Ignore cancelled deletion.
  }
}
</script>

<template>
  <div class="summary-sidebar">
    <el-card :body-style="{ padding: '16px' }" class="summary-card">
      <template #header>
        <div class="summary-header">
          <span class="summary-header__title">
            <el-icon><List /></el-icon>
            UHPC 汇总
          </span>
          <el-button size="small" text type="primary" @click="openHistory">
            <el-icon><Clock /></el-icon>
            历史记录
          </el-button>
        </div>
      </template>

      <div class="summary-group">
        <div class="group-label">基础参数</div>
        <div class="summary-row">
          <span class="row-label">配制强度 f<sub>cu,0</sub></span>
          <span class="row-val">{{ fmt(store.designStrength) }} MPa</span>
        </div>
        <div class="summary-row">
          <span class="row-label">W/B</span>
          <span class="row-val">{{ fmt(store.waterBinderRatio, 3) }}</span>
        </div>
        <div class="summary-row">
          <span class="row-label">S/B</span>
          <span class="row-val">{{ fmt(store.sandBinderRatio, 2) }}</span>
        </div>
        <div class="summary-row">
          <span class="row-label">外加剂 α</span>
          <span class="row-val">{{ fmt(store.admixtureRatio, 2) }} %</span>
        </div>
        <div class="summary-row">
          <span class="row-label">钢纤维 V<sub>f</sub></span>
          <span class="row-val">{{ fmt(store.steelFiberVolumeRatio, 2) }} %</span>
        </div>
      </div>

      <div class="summary-group">
        <div class="group-label">修正质量比例</div>
        <div class="summary-row">
          <span class="row-label">水泥</span>
          <span class="row-val">{{ fmt(store.binderMassRatios.corrected.cement) }} %</span>
        </div>
        <div class="summary-row">
          <span class="row-label">粉煤灰</span>
          <span class="row-val">{{ fmt(store.binderMassRatios.corrected.flyAsh) }} %</span>
        </div>
        <div class="summary-row">
          <span class="row-label">微珠</span>
          <span class="row-val">{{ fmt(store.binderMassRatios.corrected.microBead) }} %</span>
        </div>
        <div class="summary-row">
          <span class="row-label">硅灰</span>
          <span class="row-val">{{ fmt(store.binderMassRatios.corrected.silicaFume) }} %</span>
        </div>
      </div>

      <div class="summary-group">
        <div class="group-label">每方用量</div>
        <div class="summary-row">
          <span class="row-label">胶凝材料</span>
          <span class="row-val">{{ fmt(store.materialMasses.binder) }} kg</span>
        </div>
        <div class="summary-row">
          <span class="row-label">砂</span>
          <span class="row-val">{{ fmt(store.materialMasses.sand) }} kg</span>
        </div>
        <div class="summary-row">
          <span class="row-label">钢纤维</span>
          <span class="row-val">{{ fmt(store.materialMasses.steelFiber) }} kg</span>
        </div>
        <div class="summary-row">
          <span class="row-label">水</span>
          <span class="row-val">{{ fmt(store.materialMasses.water) }} kg</span>
        </div>
        <div class="summary-row">
          <span class="row-label">外加剂</span>
          <span class="row-val">{{ fmt(store.materialMasses.admixture) }} kg</span>
        </div>
      </div>

      <div class="summary-total">
        <span class="total-label">每方合计</span>
        <span class="total-val">{{ fmt(store.materialMasses.total) }} kg/m³</span>
      </div>

      <el-alert v-if="store.error" :title="store.error" type="error" show-icon :closable="false" style="margin-top: 12px" />
    </el-card>

    <el-dialog v-model="historyVisible" :title="historyTitle" width="950px" destroy-on-close>
      <div class="history-toolbar">
        <el-input
          v-model="historySearch"
          placeholder="搜索配比名称 / 创建人"
          clearable
          style="width: 280px"
          :prefix-icon="Search"
          @input="onHistorySearch"
          @clear="onHistorySearch"
        />
      </div>
      <el-table :data="historyItems" v-loading="historyLoading" stripe highlight-current-row max-height="420" @row-dblclick="applyRecord">
        <el-table-column prop="name" label="名称" min-width="180" />
        <el-table-column prop="created_by" label="创建人" width="100" />
        <el-table-column prop="created_at" label="创建时间" min-width="160" />
        <el-table-column prop="wb" label="W/B" width="100">
          <template #default="{ row }">{{ formatRecordNumber(row, 'wb', 3) }}</template>
        </el-table-column>
        <el-table-column prop="mb" label="胶材" width="100">
          <template #default="{ row }">{{ formatRecordNumber(row, 'mb', 1) }}</template>
        </el-table-column>
        <el-table-column prop="total_mass" label="合计(kg)" width="110" align="right">
          <template #default="{ row }">{{ formatRecordNumber(row, 'total_mass', 1) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" text @click="applyRecord(row)">载入</el-button>
            <el-button size="small" type="danger" text @click="handleDeleteRecord(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!historyLoading && historyItems.length === 0" :description="historyEmptyDescription" :image-size="80" class="history-empty" />

      <div class="history-pagination">
        <el-pagination
          v-model:current-page="historyPage"
          v-model:page-size="historyPageSize"
          :total="historyTotal"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          @current-change="onHistoryPageChange"
          @size-change="onHistorySizeChange"
        />
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.summary-header__title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 800;
  color: #1e3c72;
}

.summary-group {
  padding-bottom: 12px;
  margin-bottom: 12px;
  border-bottom: 1px solid #eef2f7;
}

.group-label {
  margin-bottom: 8px;
  color: #7b8794;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 0;
}

.row-label {
  color: #52606d;
  font-size: 13px;
}

.row-val {
  color: #1e3c72;
  font-size: 13px;
  font-weight: 700;
  text-align: right;
}

.summary-total {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-radius: 14px;
  background: linear-gradient(135deg, #0f274b, #2a5298);
  color: #fff;
}

.total-label {
  font-size: 14px;
  font-weight: 600;
}

.total-val {
  font-size: 22px;
  font-weight: 800;
}

.history-toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

.history-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.history-empty {
  padding: 24px 0 12px;
}
</style>