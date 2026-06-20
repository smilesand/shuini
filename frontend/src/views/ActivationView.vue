<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { activateLicense } from '../api/license'
import { useLicenseStore } from '../stores/licenseStore'

const router = useRouter()
const licenseStore = useLicenseStore()

const licenseCode = ref('')
const activating = ref(false)
const loading = ref(false)

const status = computed(() => licenseStore.status)
const fingerprint = computed(() => status.value?.fingerprint ?? '')
const activated = computed(() => status.value?.activated ?? false)
const isTrial = computed(() => status.value?.trial ?? false)
const trialDaysLeft = computed(() => status.value?.trial_days_left ?? null)
const expiry = computed(() => status.value?.expiry ?? null)

const statusType = computed<'success' | 'warning' | 'error' | 'info'>(() => {
  if (activated.value) return 'success'
  if (status.value && !status.value.can_use) return 'error'
  if (isTrial.value) return 'warning'
  return 'info'
})

async function refresh() {
  loading.value = true
  try {
    await licenseStore.fetchStatus()
  } finally {
    loading.value = false
  }
}

async function copyFingerprint() {
  if (!fingerprint.value) return
  try {
    await navigator.clipboard.writeText(fingerprint.value)
    ElMessage.success('指纹已复制')
  } catch {
    ElMessage.warning('复制失败，请手动选中复制')
  }
}

async function handleActivate() {
  const code = licenseCode.value.trim()
  if (!code) {
    ElMessage.warning('请输入授权码')
    return
  }
  activating.value = true
  try {
    const result = await activateLicense(code)
    if (result.activated) {
      ElMessage.success(result.message || '激活成功')
      await licenseStore.fetchStatus()
      licenseCode.value = ''
      router.push('/')
    } else {
      ElMessage.error(result.message || '激活失败')
    }
  } catch (e) {
    const msg = (e as { message?: string })?.message || '激活失败'
    ElMessage.error(msg)
  } finally {
    activating.value = false
  }
}

onMounted(refresh)
</script>

<template>
  <div class="activation-page">
    <el-card class="activation-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">软件激活</span>
          <el-button text :loading="loading" @click="refresh">刷新状态</el-button>
        </div>
      </template>

      <el-alert
        :title="status?.message || '正在获取授权状态...'"
        :type="statusType"
        :closable="false"
        show-icon
        class="status-alert"
      />

      <el-descriptions :column="1" border class="info-block">
        <el-descriptions-item label="授权状态">
          <el-tag v-if="activated" type="success">已激活</el-tag>
          <el-tag v-else-if="isTrial && status?.can_use" type="warning">
            试用中（剩余 {{ trialDaysLeft }} 天）
          </el-tag>
          <el-tag v-else type="danger">未激活</el-tag>
        </el-descriptions-item>
        <el-descriptions-item v-if="expiry" label="到期日期">{{ expiry }}</el-descriptions-item>
        <el-descriptions-item label="本机指纹">
          <div class="fingerprint-row">
            <code class="fingerprint">{{ fingerprint || '获取中...' }}</code>
            <el-button size="small" :disabled="!fingerprint" @click="copyFingerprint">复制</el-button>
          </div>
          <div class="hint">请将上方指纹发送给管理员以获取授权码。</div>
        </el-descriptions-item>
      </el-descriptions>

      <template v-if="!activated">
        <div class="form-label">授权码</div>
        <el-input
          v-model="licenseCode"
          type="textarea"
          :rows="4"
          placeholder="粘贴管理员下发的授权码..."
        />
        <el-button
          type="primary"
          class="activate-btn"
          :loading="activating"
          @click="handleActivate"
        >
          激活
        </el-button>
      </template>
    </el-card>
  </div>
</template>

<style scoped>
.activation-page {
  display: flex;
  justify-content: center;
  padding: 32px 16px;
}
.activation-card {
  width: 100%;
  max-width: 640px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  font-size: 18px;
  font-weight: 700;
}
.status-alert {
  margin-bottom: 16px;
}
.info-block {
  margin-bottom: 20px;
}
.fingerprint-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.fingerprint {
  flex: 1;
  word-break: break-all;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
  color: #1e3c72;
}
.hint {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
}
.form-label {
  font-size: 13px;
  font-weight: 700;
  color: #4a5568;
  margin-bottom: 8px;
}
.activate-btn {
  margin-top: 16px;
  width: 100%;
}
</style>
