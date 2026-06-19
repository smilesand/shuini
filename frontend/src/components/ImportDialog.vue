<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import {
  importValidate,
  importRecord,
  type ValidationItem,
  type ValidationResult,
} from '../api/exchange'

// ── Props ────────────────────────────────────────────────────────────────────

const props = defineProps<{
  visible: boolean
  projectId?: number | null
  /** 导入后是否自动保存到数据库（默认 false = 仅校验 + 载入） */
  autoSave?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  /** 校验通过后载入计算：传递解析后的数据 */
  (e: 'load', data: Record<string, unknown>, category: string): void
}>()

// ── State ────────────────────────────────────────────────────────────────────

const file = ref<File | null>(null)
const validating = ref(false)
const saving = ref(false)
const validationResult = ref<ValidationResult | null>(null)
const parsedCategory = ref<string>('hpc')
const parsedData = ref<Record<string, unknown>>({})
const step = ref<'upload' | 'result'>('upload')

// ── Computed ─────────────────────────────────────────────────────────────────

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => {
    if (!val) resetState()
    emit('update:visible', val)
  },
})

const fileName = computed(() => file.value?.name ?? '')

const allPassed = computed(() => {
  if (!validationResult.value) return false
  return validationResult.value.items.every((item) => item.passed)
})

const hasWarning = computed(() => {
  return (validationResult.value?.warnings?.length ?? 0) > 0
})

const canLoad = computed(() => {
  return parsedData.value && Object.keys(parsedData.value).length > 0
})

// ── Methods ──────────────────────────────────────────────────────────────────

function resetState() {
  file.value = null
  validationResult.value = null
  parsedCategory.value = 'hpc'
  parsedData.value = {}
  step.value = 'upload'
}

function handleFileChange(uploadFile: File | null) {
  if (!uploadFile) return
  file.value = uploadFile
  // Auto-validate after file selection
  handleValidate()
}

async function handleValidate() {
  if (!file.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  if (!file.value.name.endsWith('.xlsx')) {
    ElMessage.warning('仅支持 .xlsx 格式文件')
    return
  }

  validating.value = true
  validationResult.value = null
  try {
    if (props.autoSave) {
      // 自动保存模式：直接调用 import/record
      const res = await importRecord(file.value, props.projectId, false)
      parsedCategory.value = res.category
      parsedData.value = res.data
      validationResult.value = res.validation
      if (res.saved) {
        ElMessage.success(`记录已保存（ID: ${res.record_id}）`)
      }
    } else {
      // 仅校验模式
      const res = await importValidate(file.value)
      parsedCategory.value = res.category
      parsedData.value = res.data
      validationResult.value = res.validation
    }
    step.value = 'result'
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '校验失败'
    ElMessage.error(msg)
    validationResult.value = null
  } finally {
    validating.value = false
  }
}

function handleLoad() {
  if (!canLoad.value) {
    ElMessage.warning('没有可载入的数据')
    return
  }
  emit('load', parsedData.value, parsedCategory.value)
  dialogVisible.value = false
}

function handleDownloadTemplate() {
  const base = import.meta.env?.VITE_API_BASE || '/api'
  const category = parsedCategory.value || 'hpc'
  const url = `${base}/exchange/template?category=${category}`
  window.open(url, '_blank')
}

function handleReset() {
  resetState()
}

function getItemStatus(item: ValidationItem): 'success' | 'danger' | 'warning' {
  if (item.passed) return 'success'
  if (item.expected === null) return 'warning'
  return 'danger'
}

function formatDiff(item: ValidationItem): string {
  if (item.diff === null) return '—'
  return item.diff.toFixed(4)
}

function formatValue(val: number | null): string {
  if (val === null) return '—'
  return val.toFixed(4)
}
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    title="导入配比数据"
    width="580px"
    :close-on-click-modal="false"
    @closed="resetState"
  >
    <!-- ── Step 1: 文件上传 ───────────────────────────────────────────── -->
    <div v-if="step === 'upload'" class="import-upload">
      <p class="import-desc">
        请选择从本系统导出的 Excel 配比文件（.xlsx），系统将自动校验水胶比、砂率和粗骨料体积用量三个关键参数。
      </p>

      <div class="upload-area" @click="() => {}">
        <el-upload
          drag
          :auto-upload="false"
          :show-file-list="false"
          :on-change="(uploadFile: any) => handleFileChange(uploadFile.raw)"
          accept=".xlsx"
          class="upload-dragger"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">
            将 Excel 文件拖到此处，或<em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              仅支持 .xlsx 格式。可先
              <el-link type="primary" @click="handleDownloadTemplate">下载模板</el-link>
              参考格式。
            </div>
          </template>
        </el-upload>
      </div>

      <div v-if="fileName" class="file-selected">
        <el-tag type="info" closable @close="file = null">已选择: {{ fileName }}</el-tag>
        <el-button
          type="primary"
          size="small"
          :loading="validating"
          @click="handleValidate"
          style="margin-left: 12px"
        >
          {{ validating ? '校验中...' : '开始校验' }}
        </el-button>
      </div>
    </div>

    <!-- ── Step 2: 校验结果 ───────────────────────────────────────────── -->
    <div v-else class="import-result">
      <!-- 校验摘要 -->
      <el-result
        :icon="allPassed ? 'success' : 'error'"
        :title="allPassed ? '校验全部通过' : '校验未完全通过'"
        :sub-title="allPassed ? '所有关键参数均在容差范围内' : '部分参数超出容差范围，请检查后重新导入'"
      >
        <template v-if="!allPassed && hasWarning" #extra>
          <el-alert
            v-for="(warn, idx) in validationResult?.warnings"
            :key="idx"
            :title="warn"
            type="warning"
            show-icon
            :closable="false"
            style="margin-bottom: 8px"
          />
        </template>
      </el-result>

      <!-- 校验详情表格 -->
      <el-table
        v-if="validationResult?.items?.length"
        :data="validationResult.items"
        border
        size="small"
        style="margin-top: 16px"
      >
        <el-table-column prop="param" label="校验项" width="140" />
        <el-table-column label="重算值" width="100" align="center">
          <template #default="{ row }">
            {{ formatValue(row.expected) }}
          </template>
        </el-table-column>
        <el-table-column label="导入值" width="100" align="center">
          <template #default="{ row }">
            {{ formatValue(row.actual) }}
          </template>
        </el-table-column>
        <el-table-column label="差值" width="100" align="center">
          <template #default="{ row }">
            {{ formatDiff(row) }}
          </template>
        </el-table-column>
        <el-table-column label="容差" width="100" align="center">
          <template #default="{ row }">
            {{ row.tolerance }}
            <span v-if="row.tolerance_unit">{{ row.tolerance_unit }}</span>
          </template>
        </el-table-column>
        <el-table-column label="结果" width="80" align="center">
          <template #default="{ row }">
            <el-tag
              :type="getItemStatus(row)"
              size="small"
            >
              {{ row.passed ? '通过' : '未通过' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>

      <!-- 警告信息 -->
      <div v-if="hasWarning" style="margin-top: 12px">
        <el-alert
          v-for="(warn, idx) in validationResult?.warnings"
          :key="idx"
          :title="warn"
          type="info"
          show-icon
          :closable="false"
          style="margin-bottom: 8px"
        />
      </div>
    </div>

    <!-- ── Footer ─────────────────────────────────────────────────────── -->
    <template #footer>
      <div class="dialog-footer">
        <el-button v-if="step === 'result'" @click="handleReset">
          重新选择文件
        </el-button>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button
          v-if="step === 'result' && canLoad"
          type="primary"
          @click="handleLoad"
        >
          载入计算
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.import-upload {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.import-desc {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}

.upload-area {
  width: 100%;
}

.upload-dragger {
  width: 100%;
}

.file-selected {
  display: flex;
  align-items: center;
  margin-top: 8px;
}

.import-result {
  display: flex;
  flex-direction: column;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
