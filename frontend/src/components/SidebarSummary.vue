<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { useCalcStore } from '../stores/calcStore'
import { deleteRecord, formatRecordNumber, listRecords } from '../api/records'
import type { RecordItem } from '../api/records'
import ImportDataSection from './ImportDataSection.vue'

const store = useCalcStore()
const showImport = ref(false)
const route = useRoute()

function parseProjectId(value: unknown): number | undefined {
  const raw = Array.isArray(value) ? value[0] : value
  const projectId = Number(raw)
  return Number.isInteger(projectId) && projectId > 0 ? projectId : undefined
}

const category = computed(() => {
  if (route.path.includes('/uhpc')) return 'uhpc'
  return 'hpc'
})
const currentProjectId = computed(() => parseProjectId(route.query.project_id))
const historyTitle = computed(() => currentProjectId.value ? '当前项目配比历史记录' : '配比历史记录')
const historyEmptyDescription = computed(() => {
  if (historySearch.value) return '未找到匹配记录'
  if (currentProjectId.value) {
    return `当前项目暂无${category.value === 'uhpc' ? '超高性能' : '高性能'}混凝土配比记录`
  }
  return `暂无${category.value === 'uhpc' ? '超高性能' : '高性能'}混凝土配比记录`
})

/* ── 历史记录 ── */
const historyVisible = ref(false)
const historyItems = ref<RecordItem[]>([])
const historyLoading = ref(false)
const historyTotal = ref(0)
const historyPage = ref(1)
const historyPageSize = ref(10)
const historySearch = ref('')

function fmt(v: number | null, d = 2): string {
  return v !== null ? Number(v).toFixed(d) : '—'
}

async function fetchHistory() {
  historyLoading.value = true
  try {
    const res = await listRecords({
      category: category.value,
      project_id: currentProjectId.value,
      search: historySearch.value.trim(),
      page: historyPage.value,
      page_size: historyPageSize.value,
    })
    historyItems.value = res.items
    historyTotal.value = res.total
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '加载失败')
  } finally {
    historyLoading.value = false
  }
}

function openHistory() {
  historyVisible.value = true
  historySearch.value = ''
  historyPage.value = 1
  fetchHistory()
}

function onHistorySearch() {
  historyPage.value = 1
  fetchHistory()
}

function onHistoryPageChange(page: number) {
  historyPage.value = page
  fetchHistory()
}

function onHistorySizeChange(size: number) {
  historyPageSize.value = size
  historyPage.value = 1
  fetchHistory()
}

function applyRecord(r: RecordItem) {
  ElMessageBox.confirm(
    `确认将 "${r.name}" 的配比数据填入当前计算？`,
    '载入配比记录',
    { confirmButtonText: '确认载入', cancelButtonText: '取消', type: 'info' },
  ).then(() => {
    store.applyRecordData(r)
    ElMessage.success('载入成功，已填入当前配比记录')
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
        <div style="display:flex;align-items:center;justify-content:space-between">
          <span style="display:flex;align-items:center;gap:6px;font-size:15px;font-weight:800;color:#2a5298">
            <el-icon><List /></el-icon>
            配比汇总
          </span>
          <el-button size="small" text type="primary" @click="openHistory">
            <el-icon><Clock /></el-icon>
            历史记录
          </el-button>
        </div>
      </template>

      <ImportDataSection v-model="showImport" :imported-values="store.importedValues" category="hpc" />

      <template v-if="!showImport">

      <!-- 水胶比 & 砂率 -->
      <div class="summary-group">
        <div class="summary-row">
          <span class="row-label">
            <el-badge is-dot :type="store.wb ? 'success' : 'info'" class="dot-badge" />
            水胶比 W/B
          </span>
          <span class="row-val" :class="{ computed: store.wb }">{{ fmt(store.wb, 4) }}</span>
        </div>
        <div class="summary-row">
          <span class="row-label">
            <el-badge is-dot :type="store.sandRatioConfirmed ? 'success' : 'info'" class="dot-badge" />
            砂率 β<sub>s</sub>
          </span>
          <span class="row-val">{{ store.sandRatioConfirmed ? store.sandRatioInput + ' %' : '—' }}</span>
        </div>
      </div>

      <!-- 骨料 -->
      <div class="summary-group">
        <div class="group-label">骨料用量</div>
        <div class="summary-row">
          <span class="row-label">粗骨料 m<sub>g</sub></span>
          <span class="row-val">{{ fmt(store.mg) }} <small>kg</small></span>
        </div>
        <div class="summary-row">
          <span class="row-label">细骨料 m<sub>s</sub></span>
          <span class="row-val">{{ fmt(store.ms) }} <small>kg</small></span>
        </div>
      </div>

      <!-- 胶凝材料 -->
      <div class="summary-group">
        <div class="group-label">胶凝材料</div>
        <div class="summary-row">
          <span class="row-label">胶凝总量 m<sub>b</sub></span>
          <span class="row-val" :class="{ computed: store.mb }">{{ fmt(store.mb) }} <small>kg</small></span>
        </div>
        <div class="summary-row">
          <span class="row-label">水泥 m<sub>c</sub></span>
          <span class="row-val">{{ fmt(store.mc) }} <small>kg</small></span>
        </div>
        <div v-if="store.b1p && store.b1p > 0" class="summary-row">
          <span class="row-label">粉煤灰 m<sub>1</sub></span>
          <span class="row-val">{{ fmt(store.m1) }} <small>kg</small></span>
        </div>
        <div v-if="store.b2p && store.b2p > 0" class="summary-row">
          <span class="row-label">矿粉 m<sub>2</sub></span>
          <span class="row-val">{{ fmt(store.m2) }} <small>kg</small></span>
        </div>
        <div v-if="store.b3p && store.b3p > 0" class="summary-row">
          <span class="row-label">微珠 m<sub>3</sub></span>
          <span class="row-val">{{ fmt(store.m3) }} <small>kg</small></span>
        </div>
        <div v-if="store.b4p && store.b4p > 0" class="summary-row">
          <span class="row-label">硅灰 m<sub>4</sub></span>
          <span class="row-val">{{ fmt(store.m4) }} <small>kg</small></span>
        </div>
      </div>

      <!-- 水和外加剂 -->
      <div class="summary-group">
        <div class="group-label">水和外加剂</div>
        <div class="summary-row">
          <span class="row-label">用水量 m<sub>w</sub></span>
          <span class="row-val" :class="{ computed: store.mw }">{{ fmt(store.mw) }} <small>kg</small></span>
        </div>
        <div class="summary-row">
          <span class="row-label">外加剂 m<sub>a</sub></span>
          <span class="row-val">{{ fmt(store.ma) }} <small>kg</small></span>
        </div>
      </div>

      <!-- 合计 -->
      <div class="summary-total">
        <span class="total-label">每方合计</span>
        <span class="total-val">{{ store.totalMass ? fmt(store.totalMass) + ' kg' : '—' }}</span>
      </div>

      <el-alert
        v-if="store.error"
        :title="store.error"
        type="error"
        show-icon
        :closable="false"
        style="margin-top:10px;font-size:12px"
      />

      </template>
    </el-card>

    <!-- 历史记录对话框 -->
    <el-dialog v-model="historyVisible" :title="historyTitle" width="950px" destroy-on-close>
      <!-- 搜索栏 -->
      <div class="history-toolbar">
        <el-input
          v-model="historySearch"
          placeholder="搜索配比名称 / 创建人"
          clearable
          style="width:280px"
          :prefix-icon="Search"
          @input="onHistorySearch"
          @clear="onHistorySearch"
        />
      </div>

      <!-- 表格 -->
      <el-table
        :data="historyItems"
        v-loading="historyLoading"
        stripe
        highlight-current-row
        @row-dblclick="applyRecord"
        max-height="420"
      >
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column prop="category" label="类别" width="80">
          <template #default="{ row }">{{ row.category === 'uhpc' ? 'UHPC' : 'HPC' }}</template>
        </el-table-column>
        <el-table-column prop="created_by" label="记录人" width="100" />
        <el-table-column prop="created_at" label="创建时间" min-width="160" />
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

      <!-- 分页 -->
      <div class="history-pagination">
        <el-pagination
          v-model:current-page="historyPage"
          v-model:page-size="historyPageSize"
          :total="historyTotal"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          small
          @current-change="onHistoryPageChange"
          @size-change="onHistorySizeChange"
        />
      </div>

      <!-- 空状态 -->
      <div v-if="!historyLoading && historyItems.length === 0" class="history-empty">
        <el-empty :description="historyEmptyDescription" :image-size="80" />
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.summary-sidebar { width: 230px; flex-shrink: 0; }
.summary-card { border-radius: 12px; position: sticky; top: 0; }

.summary-group {
  padding: 8px 0;
  border-bottom: 1px solid #f0f2f5;
}
.group-label {
  font-size: 11px; font-weight: 700;
  color: #999; text-transform: uppercase;
  letter-spacing: 0.5px; margin-bottom: 4px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}

.row-label {
  font-size: 12px;
  color: #555;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}
.dot-badge { margin-right: 2px; }

.row-val {
  font-size: 13px;
  font-weight: 700;
  color: #333;
}
.row-val small { font-size: 10px; color: #999; font-weight: 400; }
.row-val.computed { color: #e67e22; }

.summary-total {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding: 12px 14px;
  background: linear-gradient(135deg, #1e3c72, #2a5298);
  border-radius: 10px;
  color: #fff;
}
.total-label { font-size: 13px; font-weight: 700; }
.total-val   { font-size: 16px; font-weight: 800; }

/* ── 历史记录对话框 ── */
.history-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.history-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

.history-empty {
  margin-top: 20px;
}
</style>
