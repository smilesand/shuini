<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteRecord, getRecordData, getRecordNumber } from '../api/records'
import type { RecordItem } from '../api/records'
import { getProject, updateProject, listProjectRecords } from '../api/projects'
import type { Project } from '../api/projects'
import { useCalcStore } from '../stores/calcStore'
import { useUhpcStore } from '../stores/uhpcStore'

interface RecordColumnDefinition {
  key: string
  label: string
  digits: number
  width: number
}

const route = useRoute()
const router = useRouter()
const store = useCalcStore()
const uhpcStore = useUhpcStore()
const projectId = Number(route.params.id)

const project = ref<Project | null>(null)
const records = ref<RecordItem[]>([])
const loading = ref(false)
const editVisible = ref(false)
const editForm = ref({ project_code: '', project_name: '', requirements: '' })
const saving = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)

const materialColumns: RecordColumnDefinition[] = [
  { key: 'mc', label: '水泥', digits: 1, width: 96 },
  { key: 'm1', label: '粉煤灰', digits: 1, width: 96 },
  { key: 'm2', label: '矿粉', digits: 1, width: 96 },
  { key: 'm3', label: '微珠', digits: 1, width: 96 },
  { key: 'm4', label: '硅灰', digits: 1, width: 96 },
  { key: 'ms', label: '细骨料', digits: 1, width: 104 },
  { key: 'mg', label: '粗骨料', digits: 1, width: 104 },
  { key: 'mw', label: '水', digits: 1, width: 96 },
  { key: 'ma', label: '外加剂', digits: 1, width: 96 },
  { key: 'steel_fiber', label: '钢纤维', digits: 1, width: 104 },
]

const parameterColumns: RecordColumnDefinition[] = [
  { key: 'mb', label: '胶材总量', digits: 1, width: 108 },
  { key: 'wb', label: '水胶比', digits: 4, width: 104 },
  { key: 'sand_ratio', label: '砂率', digits: 1, width: 96 },
  { key: 'total_mass', label: '总量', digits: 1, width: 104 },
]

const pagedRecords = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return records.value.slice(start, start + pageSize.value)
})

function fmtDate(value: string) {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

function isRecordObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function toFiniteNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function getSteelFiberValue(record: RecordItem): number | null {
  const flatValue = toFiniteNumber(record.steel_fiber)
  if (flatValue !== null) {
    return flatValue
  }

  const recordData = getRecordData(record)
  const directValue = toFiniteNumber(recordData.steel_fiber)
  if (directValue !== null) {
    return directValue
  }

  const designData = isRecordObject(recordData.design_data) ? recordData.design_data : null
  const calculated = designData && isRecordObject(designData.calculated) ? designData.calculated : null
  const materialMasses = calculated && isRecordObject(calculated.materialMasses) ? calculated.materialMasses : null
  return materialMasses ? toFiniteNumber(materialMasses.steelFiber) : null
}

function getRecordCellNumber(record: RecordItem, key: string): number | null {
  if (key === 'steel_fiber') {
    return getSteelFiberValue(record)
  }

  const storedValue = getRecordNumber(record, key)
  if (storedValue !== null) {
    return storedValue
  }

  return toFiniteNumber(record[key])
}

function formatRecordCell(record: RecordItem, key: string, digits = 1) {
  const value = getRecordCellNumber(record, key)
  return value !== null ? value.toFixed(digits) : '-'
}

function ensureCurrentPageInRange() {
  const maxPage = Math.max(1, Math.ceil(records.value.length / pageSize.value))
  if (currentPage.value > maxPage) {
    currentPage.value = maxPage
  }
}

function handlePageSizeChange() {
  currentPage.value = 1
}

async function loadProject() {
  loading.value = true
  try {
    const [p, r] = await Promise.all([
      getProject(projectId),
      listProjectRecords(projectId),
    ])
    project.value = p
    records.value = [...r].sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime())
    ensureCurrentPageInRange()
    editForm.value = { project_code: p.project_code, project_name: p.project_name, requirements: p.requirements }
  } catch (e: any) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function handleUpdate() {
  saving.value = true
  try {
    await updateProject(projectId, editForm.value)
    ElMessage.success('更新成功')
    editVisible.value = false
    loadProject()
  } catch (e: any) {
    ElMessage.error(e.message || '更新失败')
  } finally {
    saving.value = false
  }
}

function goNewCalc(category: 'hpc' | 'uhpc') {
  if (category === 'uhpc') {
    uhpcStore.resetAll()
    uhpcStore.setCurrentRecord(null, '', projectId)
  } else {
    store.resetAll()
    store.setCurrentRecord(null, '', projectId)
  }
  router.push({
    path: category === 'uhpc' ? '/calc/uhpc' : '/calc/hpc',
    query: { project_id: projectId, new: '1' },
  })
}

function openRecord(record: RecordItem) {
  if (record.category === 'uhpc') {
    uhpcStore.applyRecordData(record)
  } else {
    store.applyRecordData(record)
  }
  router.push({
    path: record.category === 'uhpc' ? '/calc/uhpc' : '/calc/hpc',
    query: { project_id: projectId },
  })
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
    if (uhpcStore.currentRecordId === record.id) {
      uhpcStore.resetAll()
    }
    ElMessage.success('已移入回收站')
    await loadProject()
  } catch {
    // Ignore cancelled deletion.
  }
}

onMounted(loadProject)
</script>

<template>
  <div v-loading="loading" class="project-detail">
    <!-- 项目信息卡片 -->
    <el-card v-if="project" style="margin-bottom:16px">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="display:flex;align-items:center;gap:8px;font-size:16px;font-weight:700;color:#1e3c72">
            <el-icon color="#2a5298"><Folder /></el-icon>
            {{ project.project_name }}
          </span>
          <el-button size="small" @click="editVisible = true">
            <el-icon><Edit /></el-icon> 编辑
          </el-button>
        </div>
      </template>
      <el-descriptions :column="3" border size="small">
        <el-descriptions-item label="项目编号">{{ project.project_code }}</el-descriptions-item>
        <el-descriptions-item label="创建人">{{ project.created_by }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ project.created_at }}</el-descriptions-item>
        <el-descriptions-item label="项目要求" :span="3">{{ project.requirements || '—' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 快捷入口 -->
    <el-card v-if="project" style="margin-bottom:16px">
      <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
        <span style="font-weight:700;color:#303133">新建配比：</span>
        <el-button type="primary" @click="goNewCalc('hpc')">
          <el-icon><Plus /></el-icon> 新建高性能混凝土
        </el-button>
        <el-button type="primary" @click="goNewCalc('uhpc')">
          <el-icon><Plus /></el-icon> 新建超高性能混凝土
        </el-button>
      </div>
    </el-card>

    <!-- 配比记录 -->
    <el-card v-if="project">
      <template #header>
        <span style="font-weight:700;color:#1e3c72">
          <el-icon><List /></el-icon> 配比记录（{{ records.length }}）
        </span>
      </template>
      <el-table v-if="records.length" :data="pagedRecords" stripe size="small" class="records-table">
        <el-table-column prop="name" label="配比名称" min-width="180" fixed="left" show-overflow-tooltip />
        <el-table-column prop="category" label="类别" width="90" align="center" fixed="left">
          <template #default="{ row }">
            <el-tag :type="row.category === 'uhpc' ? 'warning' : undefined" size="small">{{ row.category.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="配合比材料" align="center">
          <el-table-column
            v-for="column in materialColumns"
            :key="column.key"
            :label="column.label"
            :width="column.width"
            align="center"
          >
            <template #default="{ row }">{{ formatRecordCell(row, column.key, column.digits) }}</template>
          </el-table-column>
        </el-table-column>
        <el-table-column label="关键参数" align="center">
          <el-table-column
            v-for="column in parameterColumns"
            :key="column.key"
            :label="column.label"
            :width="column.width"
            align="center"
          >
            <template #default="{ row }">{{ formatRecordCell(row, column.key, column.digits) }}</template>
          </el-table-column>
        </el-table-column>
        <el-table-column prop="created_by" label="创建人" width="100" align="center" fixed="right" />
        <el-table-column label="创建时间" width="170" align="center" fixed="right">
          <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-group">
              <el-button size="small" text type="primary" @click="openRecord(row)">载入</el-button>
              <el-button size="small" text type="danger" @click="handleDeleteRecord(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无配比记录" :image-size="80" />

      <div v-if="records.length" class="records-pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="records.length"
          layout="total, sizes, prev, pager, next"
          background
          @size-change="handlePageSizeChange"
        />
      </div>
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editVisible" title="编辑项目" width="500px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="项目编号"><el-input v-model="editForm.project_code" /></el-form-item>
        <el-form-item label="项目名称"><el-input v-model="editForm.project_name" /></el-form-item>
        <el-form-item label="项目要求"><el-input v-model="editForm.requirements" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleUpdate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.records-table {
  width: 100%;
}

.records-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.action-group {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
