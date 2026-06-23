<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import {
  importProject,
  type ImportProjectResult,
  type ImportProjectRecordDetail,
  type ValidationItem,
} from '../api/exchange'

// ── Props / Emits ────────────────────────────────────────────────────────────

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'success'): void
}>()

// ── State ────────────────────────────────────────────────────────────────────

const file = ref<File | null>(null)
const validating = ref(false)
const confirming = ref(false)
const result = ref<ImportProjectResult | null>(null)
const step = ref<'upload' | 'result'>('upload')

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => {
    if (!val) resetState()
    emit('update:visible', val)
  },
})

// ── Computed ─────────────────────────────────────────────────────────────────

const fileName = computed(() => file.value?.name ?? '')
const projectInfo = computed(() => result.value?.project ?? {})
const recordDetails = computed<ImportProjectRecordDetail[]>(
  () => result.value?.record_details ?? result.value?.records ?? [],
)
const allValid = computed(() => result.value?.all_valid ?? false)
const saved = computed(() => result.value?.saved ?? false)
const savedCount = computed(() => result.value?.records_created ?? 0)
const totalCount = computed(() => result.value?.records_total ?? recordDetails.value.length)

// ── Methods ──────────────────────────────────────────────────────────────────

function resetState() {
  file.value = null
  result.value = null
  step.value = 'upload'
}

function handleFileChange(uploadFile: File | null) {
  if (!uploadFile) return
  file.value = uploadFile
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
  result.value = null
  try {
    // 第一步：仅校验，不保存
    result.value = await importProject(file.value, true)
    step.value = 'result'
    ElMessage.success(`解析完成，共 ${totalCount.value} 条记录`)
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '解析失败')
  } finally {
    validating.value = false
  }
}

async function handleConfirm() {
  if (!file.value) return
  confirming.value = true
  try {
    // 第二步：确认导入，实际保存
    result.value = await importProject(file.value, false)
    if (result.value.saved) {
      ElMessage.success(`项目导入成功，共创建 ${savedCount.value} 条记录`)
      emit('success')
    }
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '导入失败')
  } finally {
    confirming.value = false
  }
}

function getItemStatus(item: ValidationItem): 'success' | 'danger' | 'warning' {
  if (item.passed) return 'success'
  if (item.expected === null) return 'warning'
  return 'danger'
}

function formatValue(val: number | null | undefined): string {
  if (val == null) return '—'
  return val.toFixed(4)
}

function formatDiff(item: ValidationItem): string {
  if (item.diff == null) return '—'
  return item.diff.toFixed(4)
}
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    title="导入项目"
    width="700px"
    :close-on-click-modal="false"
    @closed="resetState"
  >
    <!-- ── Step 1: 上传 ───────────────────────────────────────────────── -->
    <div v-if="step === 'upload'" class="import-upload">
      <p class="import-desc">
        选择从本系统导出的项目 Excel 文件（.xlsx），系统将自动解析项目信息和所有配比记录，校验关键参数后一并导入。
      </p>
      <el-upload
        drag
        :auto-upload="false"
        :show-file-list="false"
        :on-change="(f: any) => handleFileChange(f.raw)"
        accept=".xlsx"
        class="upload-dragger"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          将项目 Excel 文件拖到此处，或<em>点击上传</em>
        </div>
      </el-upload>
      <div v-if="fileName" style="margin-top: 12px">
        <el-tag type="info" closable @close="file = null">已选择: {{ fileName }}</el-tag>
      </div>
    </div>

    <!-- ── Step 2: 结果 ───────────────────────────────────────────────── -->
    <div v-else class="import-result">
      <!-- 项目信息 -->
      <el-descriptions :column="2" border size="small" title="项目信息">
        <el-descriptions-item label="项目编号">
          {{ projectInfo.project_code || '—' }}
        </el-descriptions-item>
        <el-descriptions-item label="项目名称">
          {{ projectInfo.project_name || '—' }}
        </el-descriptions-item>
        <el-descriptions-item label="技术要求" :span="2">
          {{ projectInfo.requirements || '—' }}
        </el-descriptions-item>
      </el-descriptions>

      <!-- 导入摘要 -->
      <el-result
        v-if="!validating"
        :icon="saved ? 'success' : 'info'"
        :title="saved ? '导入完成' : '校验完成，请确认后导入'"
        :sub-title="saved
          ? `已创建项目，导入 ${savedCount}/${totalCount} 条配比记录`
          : `解析到 ${totalCount} 条配比记录，请检查校验结果后点击「确认导入」`"
        style="padding: 12px 0"
      />

      <!-- 记录详情 -->
      <div v-if="recordDetails.length" style="margin-top: 8px">
        <h4 style="margin: 0 0 8px; font-size: 14px; color: #303133">
          配比记录详情（{{ recordDetails.length }} 条）
        </h4>
        <el-collapse>
          <el-collapse-item
            v-for="(rec, idx) in recordDetails"
            :key="idx"
            :name="idx"
          >
            <template #title>
              <div style="display: flex; align-items: center; gap: 8px">
                <el-tag
                  :type="rec.saved === true ? 'success' : rec.saved === false ? 'danger' : 'info'"
                  size="small"
                >
                  {{ rec.saved === true ? '已导入' : rec.saved === false ? '失败' : '待导入' }}
                </el-tag>
                <span>{{ rec.name }}</span>
                <el-tag size="small" type="info">{{ rec.category?.toUpperCase() }}</el-tag>
              </div>
            </template>

            <div v-if="rec.error" style="margin-bottom: 8px">
              <el-alert :title="rec.error" type="error" show-icon :closable="false" />
            </div>

            <el-table
              v-if="rec.validation?.items?.length"
              :data="rec.validation.items"
              border
              size="small"
            >
              <el-table-column prop="param" label="校验项" width="140" />
              <el-table-column label="重算值" width="90" align="center">
                <template #default="{ row: item }">{{ formatValue(item.expected) }}</template>
              </el-table-column>
              <el-table-column label="导入值" width="90" align="center">
                <template #default="{ row: item }">{{ formatValue(item.actual) }}</template>
              </el-table-column>
              <el-table-column label="差值" width="90" align="center">
                <template #default="{ row: item }">{{ formatDiff(item) }}</template>
              </el-table-column>
              <el-table-column label="容差" width="90" align="center">
                <template #default="{ row: item }">
                  {{ item.tolerance }}{{ item.tolerance_unit || '' }}
                </template>
              </el-table-column>
              <el-table-column label="结果" width="80" align="center">
                <template #default="{ row: item }">
                  <el-tag :type="getItemStatus(item)" size="small">
                    {{ item.passed ? '通过' : '未通过' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
            <div
              v-for="(warn, wi) in rec.validation?.warnings"
              :key="wi"
              style="margin-top: 4px"
            >
              <el-alert :title="warn" type="info" show-icon :closable="false" />
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>

    <!-- ── Footer ─────────────────────────────────────────────────────── -->
    <template #footer>
      <div class="dialog-footer">
        <el-button v-if="step === 'result' && !saved" @click="resetState">
          重新选择文件
        </el-button>
        <el-button @click="dialogVisible = false">关闭</el-button>
        <el-button
          v-if="step === 'result' && !saved"
          type="primary"
          :loading="confirming"
          @click="handleConfirm"
        >
          确认导入
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
  margin: 0;
}
.upload-dragger {
  width: 100%;
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
