<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listRecycleBin,
  purgeProjectFromRecycleBin,
  purgeRecordFromRecycleBin,
  restoreProjectFromRecycleBin,
  restoreRecordFromRecycleBin,
  type RecycleBinFilterType,
  type RecycleBinItem,
} from '../api/recycleBin'
import { useAuthStore } from '../stores/authStore'

const authStore = useAuthStore()

const loading = ref(false)
const items = ref<RecycleBinItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const search = ref('')
const itemType = ref<RecycleBinFilterType>('all')

const pageTitle = computed(() => authStore.isAdmin ? '回收站（全部用户）' : '回收站')

function fmtDate(value?: string | null) {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

function typeLabel(value: RecycleBinItem['item_type']) {
  return value === 'project' ? '项目' : '记录'
}

function categoryLabel(item: RecycleBinItem) {
  if (item.item_type === 'project') return '项目'
  return item.category === 'uhpc' ? '超高性能' : '高性能'
}

function projectInfo(item: RecycleBinItem) {
  if (item.item_type === 'project') {
    return `${item.project_code} / ${item.project_name}`
  }
  if (!item.project_id) {
    return '未关联项目'
  }
  return `${item.project_code || '未编号'} / ${item.project_name || '未命名项目'}`
}

async function fetchItems() {
  loading.value = true
  try {
    const result = await listRecycleBin({
      item_type: itemType.value,
      search: search.value.trim() || undefined,
      page: page.value,
      page_size: pageSize.value,
    })

    if (result.total > 0 && result.items.length === 0 && page.value > 1) {
      page.value -= 1
      await fetchItems()
      return
    }

    items.value = result.items
    total.value = result.total
  } catch (e: any) {
    ElMessage.error(e.message || '加载回收站失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  void fetchItems()
}

function handleTypeChange() {
  page.value = 1
  void fetchItems()
}

function handlePageChange(value: number) {
  page.value = value
  void fetchItems()
}

function handlePageSizeChange(value: number) {
  pageSize.value = value
  page.value = 1
  void fetchItems()
}

async function handleRestore(item: RecycleBinItem) {
  const message = item.item_type === 'project'
    ? `确认恢复项目「${item.name}」？因该项目删除进入回收站的配比记录也会一并恢复。`
    : `确认恢复记录「${item.name}」？如果所属项目仍在回收站，会一并恢复该项目。`

  try {
    await ElMessageBox.confirm(message, '恢复确认', {
      confirmButtonText: '确认恢复',
      cancelButtonText: '取消',
      type: 'info',
    })

    if (item.item_type === 'project') {
      await restoreProjectFromRecycleBin(item.id)
      ElMessage.success('项目及关联记录已恢复')
    } else {
      await restoreRecordFromRecycleBin(item.id)
      ElMessage.success('记录已恢复')
    }

    await fetchItems()
  } catch {
    // Ignore cancelled restore.
  }
}

async function handlePurge(item: RecycleBinItem) {
  const message = item.item_type === 'project'
    ? `确认彻底删除项目「${item.name}」？项目及其关联记录将被物理删除，且无法恢复。`
    : `确认彻底删除记录「${item.name}」？物理删除后将无法恢复。`

  try {
    await ElMessageBox.confirm(message, '彻底删除确认', {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning',
    })

    if (item.item_type === 'project') {
      await purgeProjectFromRecycleBin(item.id)
      ElMessage.success('项目已彻底删除')
    } else {
      await purgeRecordFromRecycleBin(item.id)
      ElMessage.success('记录已彻底删除')
    }

    await fetchItems()
  } catch {
    // Ignore cancelled purge.
  }
}

onMounted(fetchItems)
</script>

<template>
  <div class="recycle-bin-view">
    <el-card class="recycle-bin-card">
      <template #header>
        <div class="recycle-bin-header">
          <span class="recycle-bin-title">
            <el-icon color="#2a5298"><Delete /></el-icon>
            {{ pageTitle }}
          </span>
          <el-tag v-if="authStore.isAdmin" type="danger" effect="plain">管理员视图</el-tag>
        </div>
      </template>

      <el-alert
        class="recycle-bin-tip"
        title="项目恢复会同步恢复因项目删除进入回收站的记录；单条记录恢复时，如果所属项目仍在回收站，也会一并恢复项目。"
        type="info"
        :closable="false"
        show-icon
      />

      <div class="recycle-bin-toolbar">
        <el-select v-model="itemType" class="recycle-bin-toolbar__select" @change="handleTypeChange">
          <el-option label="全部数据" value="all" />
          <el-option label="项目" value="project" />
          <el-option label="记录" value="record" />
        </el-select>
        <el-input
          v-model="search"
          class="recycle-bin-toolbar__search"
          placeholder="搜索名称、项目编号、项目名称、创建人"
          clearable
          @clear="handleSearch"
          @keyup.enter="handleSearch"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button @click="handleSearch">搜索</el-button>
      </div>

      <el-table v-if="items.length" :data="items" v-loading="loading" stripe class="recycle-bin-table">
        <el-table-column label="类型" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.item_type === 'project' ? 'warning' : 'info'" size="small">{{ typeLabel(row.item_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="180" show-overflow-tooltip />
        <el-table-column label="类别/状态" min-width="160" align="center">
          <template #default="{ row }">
            <div class="tag-group">
              <el-tag size="small" :type="row.item_type === 'project' ? 'warning' : undefined">{{ categoryLabel(row) }}</el-tag>
              <el-tag v-if="row.item_type === 'record' && row.deleted_with_project" size="small" type="danger">随项目删除</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="项目信息" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">{{ projectInfo(row) }}</template>
        </el-table-column>
        <el-table-column prop="created_by" label="创建人" width="100" align="center" />
        <el-table-column label="创建时间" width="170" align="center">
          <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="删除时间" width="170" align="center">
          <template #default="{ row }">{{ fmtDate(row.deleted_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-group">
              <el-button size="small" text type="primary" @click="handleRestore(row)">恢复</el-button>
              <el-button size="small" text type="danger" @click="handlePurge(row)">彻底删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-else v-loading="loading" description="回收站暂无数据" :image-size="88" />

      <div v-if="total" class="recycle-bin-pagination">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          background
          @current-change="handlePageChange"
          @size-change="handlePageSizeChange"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.recycle-bin-view {
  display: grid;
}

.recycle-bin-card {
  min-width: 0;
}

.recycle-bin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.recycle-bin-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #1e3c72;
  font-size: 16px;
  font-weight: 700;
}

.recycle-bin-tip {
  margin-bottom: 16px;
}

.recycle-bin-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.recycle-bin-toolbar__select {
  width: 140px;
}

.recycle-bin-toolbar__search {
  max-width: 360px;
}

.recycle-bin-table {
  width: 100%;
}

.recycle-bin-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.tag-group {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  flex-wrap: wrap;
}

.action-group {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}
</style>