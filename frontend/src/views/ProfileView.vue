<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Message, Lock } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '../stores/authStore'
import { getProfile, updateProfile, changePassword } from '../api/auth'

const router = useRouter()
const authStore = useAuthStore()

/* ── 个人资料 ── */
const profileFormRef = ref<FormInstance>()
const profileLoading = ref(false)
const profileForm = reactive({ email: '', phone: '' })
const profileRules: FormRules = {
  email: [{ type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }],
}

async function fetchProfile() {
  try {
    const res = await getProfile()
    profileForm.email = res.email || ''
    profileForm.phone = res.phone || ''
  } catch {
    ElMessage.error('获取个人资料失败')
  }
}

async function handleUpdateProfile() {
  const valid = await profileFormRef.value?.validate().catch(() => false)
  if (!valid) return
  profileLoading.value = true
  try {
    await updateProfile({
      email: profileForm.email.trim() || undefined,
      phone: profileForm.phone.trim() || undefined,
    })
    ElMessage.success('个人资料已更新')
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '更新失败')
  } finally {
    profileLoading.value = false
  }
}

/* ── 修改密码 ── */
const pwdFormRef = ref<FormInstance>()
const pwdLoading = ref(false)
const pwdForm = reactive({ oldPassword: '', newPassword: '', confirmPassword: '' })

const validateConfirm = (_rule: unknown, value: string, cb: (e?: Error) => void) => {
  if (value !== pwdForm.newPassword) cb(new Error('两次输入的密码不一致'))
  else cb()
}
const pwdRules: FormRules = {
  oldPassword: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 4, max: 100, message: '密码长度 4-100 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' },
  ],
}

async function handleChangePassword() {
  const valid = await pwdFormRef.value?.validate().catch(() => false)
  if (!valid) return
  pwdLoading.value = true
  try {
    await changePassword(pwdForm.oldPassword, pwdForm.newPassword)
    ElMessage.success('密码修改成功，请重新登录')
    await authStore.logout({ revokeSession: false })
    await router.push('/login')
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '密码修改失败')
  } finally {
    pwdLoading.value = false
  }
}

onMounted(() => { fetchProfile() })
</script>

<template>
  <div class="profile-page">
    <div class="profile-header">
      <div class="profile-avatar">
        <el-icon :size="48"><User /></el-icon>
      </div>
      <div class="profile-title">
        <h2>个人中心</h2>
        <p>{{ authStore.username }}</p>
      </div>
    </div>

    <el-row :gutter="24">
      <!-- 个人资料 -->
      <el-col :span="14">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><Message /></el-icon>
              <span>个人资料</span>
            </div>
          </template>
          <el-form
            ref="profileFormRef"
            :model="profileForm"
            :rules="profileRules"
            label-width="80px"
            label-position="top"
          >
            <el-form-item label="用户名">
              <el-input :model-value="authStore.username" disabled />
            </el-form-item>
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="profileForm.email" placeholder="请输入邮箱" />
            </el-form-item>
            <el-form-item label="手机号" prop="phone">
              <el-input v-model="profileForm.phone" placeholder="请输入手机号" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="profileLoading" @click="handleUpdateProfile">
                保存修改
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 修改密码 -->
      <el-col :span="10">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><Lock /></el-icon>
              <span>修改密码</span>
            </div>
          </template>
          <el-form
            ref="pwdFormRef"
            :model="pwdForm"
            :rules="pwdRules"
            label-width="80px"
            label-position="top"
          >
            <el-form-item label="原密码" prop="oldPassword">
              <el-input
                v-model="pwdForm.oldPassword"
                type="password"
                show-password
                placeholder="请输入原密码"
                autocomplete="current-password"
              />
            </el-form-item>
            <el-form-item label="新密码" prop="newPassword">
              <el-input
                v-model="pwdForm.newPassword"
                type="password"
                show-password
                placeholder="请输入新密码（至少4位）"
                autocomplete="new-password"
              />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirmPassword">
              <el-input
                v-model="pwdForm.confirmPassword"
                type="password"
                show-password
                placeholder="请再次输入新密码"
                autocomplete="new-password"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="warning" :loading="pwdLoading" @click="handleChangePassword">
                修改密码
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.profile-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 32px 24px;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 28px;
  padding: 24px;
  background: linear-gradient(135deg, #1e3c72, #2a5298);
  border-radius: 12px;
  color: #fff;
}

.profile-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(255,255,255,.2);
  display: flex;
  align-items: center;
  justify-content: center;
}

.profile-title h2 {
  margin: 0 0 4px 0;
  font-size: 22px;
  font-weight: 700;
}

.profile-title p {
  margin: 0;
  font-size: 14px;
  opacity: .8;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
</style>
