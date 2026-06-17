<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteRecord } from '../api/records'
import type { RecordItem } from '../api/records'
import { getProject, updateProject, listProjectRecords } from '../api/projects'
import type { Project } from '../api/projects'
import { useCalcStore } from '../stores/calcStore'
import { useUhpcStore } from '../stores/uhpcStore'
import RecordTable from '../components/RecordTable.vue'

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

const pagedRecords = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return records.value.slice(start, start + pageSize.value)
})

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
      <RecordTable
        :records="pagedRecords"
        :loading="loading"
        class="records-table"
      >
        <template #actions="{ row }">
          <div class="action-group">
            <el-tooltip content="载入" :show-after="300">
              <el-button size="small" text type="primary" @click="openRecord(row)">
                <el-icon><Right /></el-icon>
              </el-button>
            </el-tooltip>
            <el-tooltip content="删除" :show-after="300">
              <el-button size="small" text type="danger" @click="handleDeleteRecord(row)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
        </template>
      </RecordTable>

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
