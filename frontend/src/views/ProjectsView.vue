<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listProjects, deleteProject, createProject, listProjectRecords } from '../api/projects'
import type { Project, ProjectCreateReq } from '../api/projects'
import ImportProjectDialog from '../components/ImportProjectDialog.vue'
import { exportProjectReportPdf } from '../utils/projectReportPdf'

const router = useRouter()
const loading = ref(false)
const projects = ref<Project[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const search = ref('')

const dialogVisible = ref(false)
const creating = ref(false)
const form = ref<ProjectCreateReq>({ project_code: '', project_name: '', requirements: '' })
const importProjectVisible = ref(false)
const exportingProjectId = ref<number | null>(null)

async function fetchProjects() {
  loading.value = true
  try {
    const res = await listProjects(search.value, page.value, pageSize.value)
    projects.value = res.items
    total.value = res.total
  } catch (e: any) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function onSearch() { page.value = 1; fetchProjects() }
function onPageChange(p: number) { page.value = p; fetchProjects() }
function goDetail(id: number) { router.push(`/projects/${id}`) }

async function handleDelete(id: number, name: string) {
  try {
    await ElMessageBox.confirm(`确认删除项目「${name}」？项目及其关联配比记录会一并移入回收站，可在回收站恢复或彻底删除。`, '删除确认', { type: 'warning' })
    await deleteProject(id)
    ElMessage.success('已移入回收站')
    fetchProjects()
  } catch { }
}

async function handleCreate() {
  creating.value = true
  try {
    await createProject(form.value)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    form.value = { project_code: '', project_name: '', requirements: '' }
    fetchProjects()
  } catch (e: any) {
    ElMessage.error(e.message || '创建失败')
  } finally {
    creating.value = false
  }
}

async function handleExportProjectPdf(project: Project) {
  exportingProjectId.value = project.id
  try {
    const records = await listProjectRecords(project.id)
    if (records.length === 0) {
      ElMessage.warning('该项目下暂无配比记录可导出')
      return
    }

    await exportProjectReportPdf(project, records)
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '导出项目PDF失败')
  } finally {
    exportingProjectId.value = null
  }
}

onMounted(fetchProjects)
</script>

<template>
  <div class="projects-view">
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="display:flex;align-items:center;gap:8px;font-size:16px;font-weight:700;color:#1e3c72">
            <el-icon color="#2a5298"><Folder /></el-icon> 项目管理
          </span>
          <div style="display: flex; gap: 8px">
            <el-button @click="importProjectVisible = true">
              <el-icon><Upload /></el-icon> 导入项目
            </el-button>
            <el-button type="primary" @click="dialogVisible = true">
              <el-icon><Plus /></el-icon> 新建项目
            </el-button>
          </div>
        </div>
      </template>

      <div style="display:flex;gap:10px;margin-bottom:16px">
        <el-input v-model="search" placeholder="搜索项目编号/名称" clearable @clear="onSearch" @keyup.enter="onSearch" style="width:280px">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button @click="onSearch">搜索</el-button>
      </div>

      <el-table :data="projects" v-loading="loading" stripe style="width:100%">
        <el-table-column prop="project_code" label="项目编号" min-width="140" />
        <el-table-column prop="project_name" label="项目名称" min-width="200">
          <template #default="{ row }">
            <el-link type="primary" @click="goDetail(row.id)">{{ row.project_name }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="requirements" label="项目要求" min-width="240" show-overflow-tooltip />
        <el-table-column prop="created_by" label="创建人" width="100" />
        <el-table-column prop="record_count" label="配比数" width="80" align="center" />
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="220" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-group">
              <el-tooltip content="详情" :show-after="300">
                <el-button size="small" text type="primary" @click="goDetail(row.id)">
                  <el-icon><InfoFilled /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="导出项目PDF" :show-after="300">
                <el-button
                  size="small"
                  text
                  type="success"
                  :loading="exportingProjectId === row.id"
                  @click="handleExportProjectPdf(row)"
                >
                  <el-icon><Printer /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="删除" :show-after="300">
                <el-button size="small" text type="danger" @click="handleDelete(row.id, row.project_name)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > pageSize"
        style="margin-top:16px;justify-content:flex-end"
        :current-page="page" :page-size="pageSize" :total="total"
        layout="total, prev, pager, next" @current-change="onPageChange"
      />
    </el-card>

    <!-- 新建项目对话框 -->
    <el-dialog v-model="dialogVisible" title="新建项目" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="项目编号" required>
          <el-input v-model="form.project_code" placeholder="" />
        </el-form-item>
        <el-form-item label="项目名称" required>
          <el-input v-model="form.project_name" placeholder="如 某某大桥C50混凝土" />
        </el-form-item>
        <el-form-item label="项目要求">
          <el-input v-model="form.requirements" type="textarea" :rows="3" placeholder="强度等级、耐久性等要求" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 导入项目对话框 -->
    <ImportProjectDialog
      v-model:visible="importProjectVisible"
      @success="fetchProjects"
    />
  </div>
</template>

<style scoped>
.action-group {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
