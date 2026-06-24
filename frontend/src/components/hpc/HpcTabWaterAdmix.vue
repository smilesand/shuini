<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useCalcStore } from '../../stores/calcStore.ts'
import { saveRecord } from '../../api/records.ts'
import { debounce } from '../../utils/debounce.ts'
import Formula from '../Formula.vue'
import '../../style/calc-tabs.css'

const store = useCalcStore()
const route = useRoute()
const saveVisible = ref(false)
const saveName = ref('')
const saving = ref(false)

const category = computed<'hpc' | 'uhpc'>(() => route.path.includes('/uhpc') ? 'uhpc' : 'hpc')
const currentProjectId = computed<number | null>(() => {
  // 优先取路由中的 project_id；从菜单返回计算器时路由可能未带该参数，
  // 此时回退到 store 中记录的项目，避免保存的记录 project_id 为空而在「配合比记录」中不可见。
  const pid = route.query.project_id
  if (pid !== undefined && pid !== null && pid !== '') {
    const n = Number(Array.isArray(pid) ? pid[0] : pid)
    if (Number.isInteger(n) && n > 0) return n
  }
  if (store.currentRecordProjectId != null) return store.currentRecordProjectId
  return store.hpcSelectedProjectId ?? null
})
const canUpdateCurrentRecord = computed(() => (
  store.currentRecordId !== null
  && !!store.currentRecordName.trim()
  && store.currentRecordProjectId === currentProjectId.value
))
const saveButtonText = computed(() => canUpdateCurrentRecord.value ? '保存修改' : '保存配比记录')

// 防抖计算：外加剂掺量变化后 500ms 自动重算
const debouncedCalc = debounce(() => store.calcWaterAdmixture(), 500)

watch(
  () => [store.alpha, store.mb, store.wb] as const,
  () => {
    if (store.alpha && store.mb && store.wb) {
      debouncedCalc()
    }
  },
)

async function handleFinish() {
  await store.calcWaterAdmixture()
  if (store.totalMass === null) return

  if (canUpdateCurrentRecord.value) {
    await persistRecord(store.currentRecordName)
    return
  }

  saveName.value = store.currentRecordName
  saveVisible.value = true
}

async function persistRecord(name: string) {
  const finalName = name.trim()
  if (!finalName) return

  const isUpdate = canUpdateCurrentRecord.value
  saving.value = true
  try {
    const res = await saveRecord(store.buildRecordPayload(
      category.value,
      finalName,
      currentProjectId.value,
      isUpdate ? store.currentRecordId : null,
    ))
    store.markRecordSaved(res.id, finalName, currentProjectId.value)
    saveVisible.value = false
    saveName.value = finalName
    ElMessage.success(isUpdate ? '更新成功' : '保存成功')
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || (isUpdate ? '更新失败' : '保存失败'))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <!-- 依据参数 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><Drizzling /></el-icon>
        依据参数
      </div>
      <div class="cs-section-body">
        <el-descriptions :column="2" size="small" border class="inherited-desc">
          <el-descriptions-item >
<template #label>胶凝材料用量 m<sub>b</sub></template>
            <span class="inherited-val">{{ store.mb ? store.mb.toFixed(2) + ' kg' : '—' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="水胶比 (W/B)">
            <span class="inherited-val">{{ store.wb ? store.wb.toFixed(4) : '—' }}</span>
          </el-descriptions-item>
        </el-descriptions>
        <el-alert
          v-if="!store.mb || !store.wb"
          title="请先完成胶凝材料计算"
          type="warning" show-icon :closable="false"
          style="margin-top:10px"
        />
      </div>
    </div>

    <!-- 外加剂参数 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><EditPen /></el-icon>
        外加剂参数
      </div>
      <div class="cs-section-body">
        <el-form label-position="top">
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="外加剂掺量 α">
                <el-input-number
                  :model-value="store.alpha ?? undefined"
                  @update:model-value="v => store.alpha = v ?? null"
                  :min="0" :step="0.1" :precision="2"
                  placeholder=""
                  style="width:100%"
                >
                  <template #suffix><span class="unit-suffix">%</span></template>
                </el-input-number>
                <div class="input-hint">参考掺量 1.5 %</div>
                <div v-if="store.importedValueText('alpha', ' %', 2)" class="input-hint">{{ store.importedValueText('alpha', ' %', 2) }}</div>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </div>
    </div>

    <!-- 计算结果 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><Histogram /></el-icon>
        计算结果
      </div>
      <div class="cs-section-body">
        <el-form label-position="top">
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item>
                <template #label>用水量 m<sub>w</sub></template>
                <el-input :value="store.mw ? store.mw.toFixed(2) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">kg</span></template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item>
                <template #label>外加剂用量 m<sub>a</sub></template>
                <el-input :value="store.ma ? store.ma.toFixed(2) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">kg</span></template>
                </el-input>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>

        <!-- 总合计 -->
        <div class="total-card">
          <span class="total-label">每立方混凝土材料合计</span>
          <span class="total-val">{{ store.totalMass ? store.totalMass.toFixed(2) + ' kg/m³' : '—' }}</span>
        </div>

        <el-alert type="info" :closable="false" style="margin-top:12px">
          <template #title>计算公式说明</template>
          <template #default>
            <Formula latex="m_w = m_b \times W\!/\!B" style="margin-bottom:8px" />
            <Formula latex="m_a = m_b \times \alpha" />
          </template>
        </el-alert>

        <el-alert
          v-if="store.mw !== null"
          title="全部计算已完成！可在右侧汇总栏查看完整配比结果。"
          type="success"
          :closable="false"
          show-icon
          style="margin-top:12px"
        />

        <div class="footer-actions">
          <el-button
            type="primary"
            :loading="store.loading"
            :disabled="!store.mb || !store.wb || !store.alpha"
            @click="handleFinish"
          >
            {{ saveButtonText }}
            <el-icon><FolderAdd /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <el-dialog v-model="saveVisible" title="保存配比记录" width="400px">
      <el-form @submit.prevent="persistRecord(saveName)">
        <el-form-item label="配比名称">
          <el-input v-model="saveName" placeholder="例如：C80 高性能混凝土方案" maxlength="50" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="saveVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" :disabled="!saveName.trim()" @click="persistRecord(saveName)">
          确认保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.total-card {
  margin-top: 16px;
  padding: 16px 20px;
  background: linear-gradient(135deg, #1e3c72, #2a5298);
  border-radius: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.total-label {
  font-size: 14px;
  color: rgba(255,255,255,0.85);
  font-weight: 500;
}
.total-val {
  font-size: 22px;
  font-weight: 800;
  color: #fff;
}
</style>
