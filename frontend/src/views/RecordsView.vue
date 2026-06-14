<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getRecordObject, getRecordNumber, listRecords, type RecordItem } from '../api/records'
import { listProjects } from '../api/projects'
import { useCalcStore } from '../stores/calcStore'
import { useUhpcStore } from '../stores/uhpcStore'

const router = useRouter()
const calcStore = useCalcStore()
const uhpcStore = useUhpcStore()

const loading = ref(false)
const records = ref<RecordItem[]>([])
const projectNames = ref<Record<number, string>>({})
const search = ref('')
const category = ref<'all' | 'hpc' | 'uhpc'>('all')
const page = ref(1)
const pageSize = ref(10)

function fmtDate(value: string) {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

function extractTrialValue(record: RecordItem, key: string): number | null {
  const trialData = getRecordObject(record, 'trial_data')
  if (!trialData) {
    return null
  }

  const inputs = trialData.inputs as Record<string, unknown> | undefined
  const val = inputs ? inputs[key] : trialData[key]
  if (typeof val === 'number' && Number.isFinite(val)) {
    return val
  }
  return null
}

function strength28dDisplay(record: RecordItem): string {
  const trialVal = extractTrialValue(record, 'evalStrength28d')
  if (trialVal !== null) {
    return `${trialVal.toFixed(1)} MPa`
  }

  const fcu0 = getRecordNumber(record, 'fcu0')
  return fcu0 !== null ? `${fcu0.toFixed(1)} MPa` : '—'
}

function slumpDisplay(record: RecordItem): string {
  const evalSlump = extractTrialValue(record, 'evalSlump')
  if (evalSlump !== null) {
    return `${evalSlump.toFixed(0)} mm`
  }

  const slumpMeasured = extractTrialValue(record, 'slumpMeasured')
  if (slumpMeasured !== null) {
    return `${slumpMeasured.toFixed(0)} mm`
  }

  return '—'
}

function spreadDisplay(record: RecordItem): string {
  const evalSpread = extractTrialValue(record, 'evalSpread')
  if (evalSpread !== null) {
    return `${evalSpread.toFixed(0)} mm`
  }

  const spreadMeasured = extractTrialValue(record, 'spreadMeasured')
  if (spreadMeasured !== null) {
    return `${spreadMeasured.toFixed(0)} mm`
  }

  return '—'
}

function wbDisplay(record: RecordItem): string {
  const wb = getRecordNumber(record, 'wb')
  return wb !== null ? wb.toFixed(4) : '—'
}

function sandRatioDisplay(record: RecordItem): string {
  const sr = getRecordNumber(record, 'sand_ratio')
  return sr !== null ? `${sr.toFixed(1)} %` : '—'
}

function totalMassDisplay(record: RecordItem): string {
  const total = getRecordNumber(record, 'total_mass')
  return total !== null ? total.toFixed(0) : '—'
}

function categoryTag(value: string): 'primary' | 'warning' {
  return value === 'uhpc' ? 'warning' : 'primary'
}

function categoryLabel(value: string) {
  return value === 'uhpc' ? 'UHPC' : 'HPC'
}

function getProjectName(record: RecordItem) {
  if (typeof record.project_id === 'number' && projectNames.value[record.project_id]) {
    return projectNames.value[record.project_id]
  }

  return '未关联项目'
}

const filteredRecords = computed(() => {
  const keyword = search.value.trim().toLowerCase()

  return [...records.value]
    .sort((left, right) => {
      const leftTime = new Date(left.created_at).getTime()
      const rightTime = new Date(right.created_at).getTime()
      return rightTime - leftTime
    })
    .filter((record) => category.value === 'all' || record.category === category.value)
    .filter((record) => {
      if (!keyword) {
        return true
      }

      const projectName = getProjectName(record).toLowerCase()
      const recordName = String(record.name ?? '').toLowerCase()
      return projectName.includes(keyword) || recordName.includes(keyword)
    })
})

const pagedRecords = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredRecords.value.slice(start, start + pageSize.value)
})

async function loadRecords() {
  loading.value = true
  try {
    const [recordResult, projectResult] = await Promise.all([
      listRecords({ page: 1, page_size: 1000 }),
      listProjects('', 1, 1000),
    ])

    records.value = recordResult.items
    projectNames.value = projectResult.items.reduce<Record<number, string>>((map, project) => {
      map[project.id] = project.project_name
      return map
    }, {})
  } catch (error: unknown) {
    ElMessage.error(error instanceof Error ? error.message : '配合记录加载失败')
    records.value = []
    projectNames.value = {}
  } finally {
    loading.value = false
  }
}

function handleFilterChange() {
  page.value = 1
}

function loadRecord(record: RecordItem) {
  if (record.category === 'uhpc') {
    uhpcStore.applyRecordData(record)
    router.push({
      path: '/calc/uhpc',
      query: record.project_id ? { project_id: record.project_id } : {},
    })
    return
  }

  calcStore.applyRecordData(record)
  router.push({
    path: '/calc/hpc',
    query: record.project_id ? { project_id: record.project_id } : {},
  })
}

onMounted(() => {
  void loadRecords()
})
</script>

<template>
  <div class="records-view">
    <el-card v-loading="loading" class="records-card">
      <template #header>
        <div class="records-header">
          <div class="records-title">
            <el-icon color="#2a5298"><Document /></el-icon>
            <span>全部配合记录</span>
          </div>
          <el-button type="primary" plain @click="loadRecords">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <div class="records-toolbar">
        <el-input
          v-model="search"
          placeholder="搜索项目名称或配比名称"
          clearable
          class="records-toolbar__search"
          @input="handleFilterChange"
          @clear="handleFilterChange"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>

        <el-select v-model="category" class="records-toolbar__select" @change="handleFilterChange">
          <el-option label="全部类别" value="all" />
          <el-option label="HPC" value="hpc" />
          <el-option label="UHPC" value="uhpc" />
        </el-select>
      </div>

      <el-table v-if="filteredRecords.length" :data="pagedRecords" stripe size="small" class="records-table">
        <el-table-column label="项目名称" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            {{ getProjectName(row) }}
          </template>
        </el-table-column>
        <el-table-column prop="name" label="配比名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="category" label="类别" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="categoryTag(row.category)" size="small">{{ categoryLabel(row.category) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="28d抗压强度" width="130" align="center">
          <template #default="{ row }">{{ strength28dDisplay(row) }}</template>
        </el-table-column>
        <el-table-column label="实测坍落度" width="110" align="center">
          <template #default="{ row }">{{ slumpDisplay(row) }}</template>
        </el-table-column>
        <el-table-column label="实测扩展度" width="110" align="center">
          <template #default="{ row }">{{ spreadDisplay(row) }}</template>
        </el-table-column>
        <el-table-column label="水胶比" width="100" align="center">
          <template #default="{ row }">{{ wbDisplay(row) }}</template>
        </el-table-column>
        <el-table-column label="砂率" width="90" align="center">
          <template #default="{ row }">{{ sandRatioDisplay(row) }}</template>
        </el-table-column>
        <el-table-column label="总量" width="90" align="center">
          <template #default="{ row }">{{ totalMassDisplay(row) }}</template>
        </el-table-column>
        <el-table-column prop="created_by" label="创建人" width="110" align="center" />
        <el-table-column label="时间" width="170" align="center">
          <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right" align="center">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="loadRecord(row)">载入</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-else description="暂无配合记录" :image-size="88" />

      <div v-if="filteredRecords.length" class="records-pagination">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="filteredRecords.length"
          layout="total, sizes, prev, pager, next"
          background
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.records-view {
  display: grid;
}

.records-card {
  min-width: 0;
}

.records-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.records-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #1e3c72;
  font-size: 16px;
  font-weight: 700;
}

.records-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.records-toolbar__search {
  max-width: 320px;
}

.records-toolbar__select {
  width: 150px;
}

.records-table {
  width: 100%;
}

.records-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>