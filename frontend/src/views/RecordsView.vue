<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listRecords, type RecordItem } from '../api/records'
import RecordTable from '../components/RecordTable.vue'
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

      <RecordTable
        :records="pagedRecords"
        :loading="loading"
        show-project-name
        :get-project-name="getProjectName"
        class="records-table"
      >
        <template #actions="{ row }">
          <el-tooltip content="载入" :show-after="300">
            <el-button size="small" text type="primary" @click="loadRecord(row)">
              <el-icon><Right /></el-icon>
            </el-button>
          </el-tooltip>
        </template>
      </RecordTable>

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