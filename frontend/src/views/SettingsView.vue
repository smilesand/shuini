<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, InfoFilled } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import { createUser, listUsers, deleteUser, adminResetPassword, type UserInfo } from '../api/auth'

/* ── 用户列表 ── */
const users = ref<UserInfo[]>([])
const loading = ref(false)
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(10)

const filteredUsers = computed(() => {
  if (!searchKeyword.value.trim()) return users.value
  const kw = searchKeyword.value.trim().toLowerCase()
  return users.value.filter(u =>
    u.username.toLowerCase().includes(kw) ||
    u.email.toLowerCase().includes(kw) ||
    u.phone.includes(kw)
  )
})

const pagedUsers = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredUsers.value.slice(start, start + pageSize.value)
})

/* ── 新增用户弹窗 ── */
const createVisible = ref(false)
const createFormRef = ref<FormInstance>()
const createLoading = ref(false)
const createForm = reactive({ username: '', email: '', phone: '' })
const createRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 50, message: '用户名长度 2-50 位', trigger: 'blur' },
  ],
  email: [{ type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }],
}

async function handleCreate() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return
  createLoading.value = true
  try {
    await createUser({
      username: createForm.username.trim(),
      email: createForm.email.trim(),
      phone: createForm.phone.trim(),
    })
    ElMessage.success(`用户 "${createForm.username}" 创建成功，默认密码 123456`)
    createVisible.value = false
    createForm.username = ''
    createForm.email = ''
    createForm.phone = ''
    createFormRef.value?.resetFields()
    await fetchUsers()
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '创建用户失败')
  } finally {
    createLoading.value = false
  }
}

/* ── 重置密码弹窗 ── */
const resetVisible = ref(false)
const resetTarget = ref('')
const resetFormRef = ref<FormInstance>()
const resetLoading = ref(false)
const resetForm = reactive({ password: '', confirm: '' })

const validateConfirm = (_rule: unknown, value: string, cb: (e?: Error) => void) => {
  if (value !== resetForm.password) cb(new Error('两次输入的密码不一致'))
  else cb()
}
const resetRules: FormRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 4, max: 100, message: '密码长度 4-100 位', trigger: 'blur' },
  ],
  confirm: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' },
  ],
}

function openResetDialog(user: UserInfo) {
  resetTarget.value = user.username
  resetForm.password = ''
  resetForm.confirm = ''
  resetFormRef.value?.resetFields()
  resetVisible.value = true
}

async function handleReset() {
  const valid = await resetFormRef.value?.validate().catch(() => false)
  if (!valid) return
  resetLoading.value = true
  try {
    await adminResetPassword(resetTarget.value, resetForm.password)
    ElMessage.success(`用户 "${resetTarget.value}" 密码已重置`)
    resetVisible.value = false
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '密码重置失败')
  } finally {
    resetLoading.value = false
  }
}

/* ── 删除确认 ── */
async function handleDelete(user: UserInfo) {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户「${user.username}」吗？此操作不可恢复。`,
      '删除用户确认',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteUser(user.username)
    ElMessage.success(`用户 "${user.username}" 已删除`)
    await fetchUsers()
  } catch (e: unknown) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error((e as Error).message || '删除用户失败')
    }
  }
}

/* ── 获取用户列表 ── */
async function fetchUsers() {
  loading.value = true
  try {
    users.value = await listUsers()
    currentPage.value = 1
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '获取用户列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => { fetchUsers() })
</script>

<template>
  <div class="settings-page">
    <!-- 工具栏 -->
    <div class="toolbar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索用户名 / 邮箱 / 手机号"
        clearable
        style="width:300px"
        :prefix-icon="Search"
        @input="currentPage = 1"
      />
      <el-button type="primary" @click="createVisible = true">
        <el-icon><Plus /></el-icon>
        新增用户
      </el-button>
    </div>

    <!-- 用户表格 -->
    <el-card shadow="never" class="table-card">
      <el-table
        :data="pagedUsers"
        v-loading="loading"
        stripe
        border
        style="width:100%"
        :header-cell-style="{ background:'#f5f7fa', color:'#303133', fontWeight:600 }"
      >
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="email" label="邮箱" min-width="160">
          <template #default="{ row }">
            <span v-if="row.email">{{ row.email }}</span>
            <span v-else style="color:#c0c4cc">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="phone" label="手机号" min-width="130">
          <template #default="{ row }">
            <span v-if="row.phone">{{ row.phone }}</span>
            <span v-else style="color:#c0c4cc">—</span>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_admin ? 'danger' : 'info'" size="small" effect="plain">
              {{ row.is_admin ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="密码状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.must_reset ? 'warning' : 'success'" size="small" effect="plain">
              {{ row.must_reset ? '待重置' : '正常' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="160" />
        <el-table-column label="操作" width="180" align="center" fixed="right">
          <template #default="{ row }">
            <el-button text type="warning" size="small" @click="openResetDialog(row)">
              重置密码
            </el-button>
            <el-popconfirm
              v-if="!row.is_admin"
              title="确定删除该用户？"
              confirm-button-text="删除"
              cancel-button-text="取消"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button text type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="filteredUsers.length"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
        />
      </div>
    </el-card>

    <!-- ── 新增用户对话框 ── -->
    <el-dialog v-model="createVisible" title="新增用户" width="460px" :close-on-click-modal="false" destroy-on-close>
      <p class="dialog-hint">
        <el-icon><InfoFilled /></el-icon>
        新用户默认密码为 <el-tag type="warning" size="small">123456</el-tag>，首次登录后须修改密码。
      </p>
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-width="80px"
        @submit.prevent="handleCreate"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="createForm.username" placeholder="请输入用户名（必填）" autocomplete="off" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="createForm.email" placeholder="选填" autocomplete="off" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="createForm.phone" placeholder="选填" autocomplete="off" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="handleCreate">确认创建</el-button>
      </template>
    </el-dialog>

    <!-- ── 重置密码对话框 ── -->
    <el-dialog v-model="resetVisible" title="重置密码" width="420px" :close-on-click-modal="false" destroy-on-close>
      <p style="margin-bottom:16px;color:#606266;">
        正在为用户 <el-tag type="warning" size="small">{{ resetTarget }}</el-tag> 重置密码
      </p>
      <el-form
        ref="resetFormRef"
        :model="resetForm"
        :rules="resetRules"
        label-width="80px"
        @submit.prevent="handleReset"
      >
        <el-form-item label="新密码" prop="password">
          <el-input v-model="resetForm.password" type="password" placeholder="请输入新密码" show-password autocomplete="new-password" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm">
          <el-input v-model="resetForm.confirm" type="password" placeholder="请再次输入新密码" show-password autocomplete="new-password" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetVisible = false">取消</el-button>
        <el-button type="primary" :loading="resetLoading" @click="handleReset">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.settings-page {
  width: 100%;
  height: 100%;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.table-card {
  border-radius: 8px;
}

.table-card :deep(.el-card__body) {
  padding: 20px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.dialog-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  margin-bottom: 18px;
  background: #fdf6ec;
  border: 1px solid #faecd8;
  border-radius: 8px;
  color: #b88230;
  font-size: 13px;
}
</style>
