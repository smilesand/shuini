<script setup lang="ts">
import { computed, watch } from 'vue'
import { useCalcStore } from '../../stores/calcStore.ts'
import { debounce } from '../../utils/debounce.ts'
import {
  HPC_WORKABILITY_REFERENCES,
  getHpcWorkabilityReference,
  matchHpcWorkabilityReferences,
  resolveHpcWorkabilityCode,
} from '../../utils/hpcWorkability.ts'
import Formula from '../Formula.vue'
import '../../style/calc-tabs.css'

const emit = defineEmits<{ (e: 'next-step'): void }>()
const store = useCalcStore()

// 防抖计算：输入变化后 500ms 自动重算
const debouncedCalc = debounce(() => store.calcAggregate(), 500)

watch(
  () => [store.vg, store.rhog, store.rhos, store.sandRatioConfirmed, store.sandRatioInput] as const,
  () => {
    if (store.vg && store.rhog && store.rhos && store.sandRatioConfirmed && store.sandRatioInput) {
      debouncedCalc()
    }
  },
)

async function handleNext() {
  await store.calcAggregate()
  emit('next-step')
}

const vgTableData = HPC_WORKABILITY_REFERENCES

// 根据用户输入的工作性能要求（坍落度 / 扩展度）自动匹配工作性等级
const matchedCodes = computed(() =>
  matchHpcWorkabilityReferences(store.reqSlump, store.reqSpread),
)

// 输入变化时自动确定 Vg 参考等级（取第一个命中项）
watch(
  () => [store.reqSlump, store.reqSpread] as const,
  () => {
    store.vgReferenceCode = resolveHpcWorkabilityCode(store.reqSlump, store.reqSpread)
  },
)

const selectedVgReference = computed(() => getHpcWorkabilityReference(store.vgReferenceCode))

const selectedVgRange = computed(() => {
  return selectedVgReference.value?.range.replace(/\s+/g, '') ?? null
})

const vgPlaceholder = computed(() => selectedVgRange.value ?? '如 0.35')

function resolveWorkabilityRowClassName({ row }: { row: (typeof vgTableData)[number] }) {
  return matchedCodes.value.includes(row.code) ? 'is-selected-row' : ''
}
</script>

<template>
  <div>
    <!-- 依据参数 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><InfoFilled /></el-icon>
        依据参数
      </div>
      <div class="cs-section-body">
        <el-descriptions :column="1" size="small" border class="inherited-desc">
          <el-descriptions-item>
            <template #label>砂率 <span class="math-token">β<sub class="math-sub">s</sub></span></template>
            <span class="inherited-val">{{ store.sandRatioConfirmed ? store.sandRatioInput + ' %' : '—' }}</span>
          </el-descriptions-item>
        </el-descriptions>
        <el-alert
          v-if="!store.sandRatioConfirmed"
          title="请先在「砂率选取」标签页确认砂率"
          type="warning" show-icon :closable="false"
          style="margin-top:10px"
        />
      </div>
    </div>

    <!-- 工作性能要求 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><Grid /></el-icon>
        工作性能要求
      </div>
      <div class="cs-section-body">
        <el-form label-position="top">
          <el-row :gutter="20" style="margin-bottom:8px">
            <el-col :span="12">
              <el-form-item label="坍落度">
                <el-input-number
                  :model-value="store.reqSlump ?? undefined"
                  @update:model-value="v => store.reqSlump = v ?? null"
                  :step="10" :precision="0" :min="0"
                  style="width:100%"
                >
                  <template #suffix><span class="unit-suffix">mm</span></template>
                </el-input-number>
                <div class="input-hint">参考值 180~220 mm（SF0 大流动度）</div>
                <div v-if="store.importedValueText('req_slump', ' mm', 0)" class="input-hint">{{ store.importedValueText('req_slump', ' mm', 0) }}</div>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="扩展度">
                <el-input-number
                  :model-value="store.reqSpread ?? undefined"
                  @update:model-value="v => store.reqSpread = v ?? null"
                  :step="10" :precision="0" :min="0"
                  style="width:100%"
                >
                  <template #suffix><span class="unit-suffix">mm</span></template>
                </el-input-number>
                <div class="input-hint">参考值 500~800 mm（SF1~SF3）</div>
                <div v-if="store.importedValueText('req_spread', ' mm', 0)" class="input-hint">{{ store.importedValueText('req_spread', ' mm', 0) }}</div>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
        <el-table
          :data="vgTableData"
          border
          size="small"
          style="margin-bottom:8px"
          :row-class-name="resolveWorkabilityRowClassName"
          class="vg-ref-table"
        >
          <el-table-column prop="code"  label="工作性等级"        width="110"  align="center" />
          <el-table-column prop="desc"  label="坍落度/扩展度范围" align="center" />
          <el-table-column prop="range" label="Vg 范围 (m³)" width="160" align="center" />
        </el-table>
        <p style="font-size:11px;color:#909399;margin-bottom:8px">表格依据输入的坍落度/扩展度自动高亮匹配的工作性等级；空隙率 &gt;41% 取偏小值，&lt;41% 取偏大值</p>
        <el-alert
          v-if="selectedVgRange"
          :title="`当前匹配的 Vg 参考范围：${selectedVgRange} m³`"
          type="success"
          :closable="false"
          show-icon
        />
        <el-alert
          v-else
          title="请在上方输入坍落度或扩展度以自动匹配 Vg 参考范围"
          type="error"
          :closable="false"
          show-icon
        />
      </div>
    </div>

    <!-- 骨料参数输入 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><EditPen /></el-icon>
        骨料参数输入
      </div>
      <div class="cs-section-body">
        <el-form label-position="top">
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item>
                <template #label>粗骨料绝对体积 <span class="math-token">V<sub class="math-sub">g</sub></span></template>
                <el-input-number
                  :model-value="store.vg ?? undefined"
                  @update:model-value="v => store.vg = v ?? null"
                  :step="0.01" :precision="3"
                  placeholder=""
                  style="width:100%"
                >
                  <template #suffix><span class="unit-suffix">m³</span></template>
                </el-input-number>
                <div class="input-hint">参考选值 {{ vgPlaceholder }}<template v-if="store.importedValueText('vg', ' m³', 3)">，{{ store.importedValueText('vg', ' m³', 3) }}</template></div>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item>
                <template #label><span class="math-token">ρ<sub class="math-sub">g</sub></span> 粗骨料密度</template>
                <el-input-number
                  :model-value="store.rhog ?? undefined"
                  @update:model-value="v => store.rhog = v ?? null"
                  :step="50" :precision="0"
                  placeholder=""
                  style="width:100%"
                >
                  <template #suffix><span class="unit-suffix">kg/m³</span></template>
                </el-input-number>
                <div class="input-hint">参考值 2700 kg/m³<template v-if="store.importedValueText('rhog', ' kg/m³', 0)">，{{ store.importedValueText('rhog', ' kg/m³', 0) }}</template></div>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item>
                <template #label><span class="math-token">ρ<sub class="math-sub">s</sub></span> 细骨料密度</template>
                <el-input-number
                  :model-value="store.rhos ?? undefined"
                  @update:model-value="v => store.rhos = v ?? null"
                  :step="50" :precision="0"
                  placeholder=""
                  style="width:100%"
                >
                  <template #suffix><span class="unit-suffix">kg/m³</span></template>
                </el-input-number>
                <div class="input-hint">参考值 2650 kg/m³<template v-if="store.importedValueText('rhos', ' kg/m³', 0)">，{{ store.importedValueText('rhos', ' kg/m³', 0) }}</template></div>
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
            <el-col :span="12">
              <el-form-item>
                <template #label>粗骨料用量 <span class="math-token">m<sub class="math-sub">g</sub></span></template>
                <el-input :value="store.mg ? store.mg.toFixed(2) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">kg</span></template>
                </el-input>
                <div v-if="store.importedValueText('mg', ' kg', 2)" class="input-hint">{{ store.importedValueText('mg', ' kg', 2) }}</div>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item>
                <template #label>细骨料用量 <span class="math-token">m<sub class="math-sub">s</sub></span></template>
                <el-input :value="store.ms ? store.ms.toFixed(2) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">kg</span></template>
                </el-input>
                <div v-if="store.importedValueText('ms', ' kg', 2)" class="input-hint">{{ store.importedValueText('ms', ' kg', 2) }}</div>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>

        <el-alert type="info" :closable="false" style="margin-top:8px">
          <template #title>计算公式说明</template>
          <template #default>
            <Formula latex="m_{g} = V_{g} \cdot \rho_{g}" style="margin-bottom:8px" />
            <Formula latex="m_{s} = \frac{\beta_{s}}{\,1 - \beta_{s}\,} \cdot m_{g}" />
            <p style="margin-top:8px;font-size:12px;color:#999">
              粗骨料质量 = 体积 × 密度；细骨料由砂率反推。<span class="math-token">β<sub class="math-sub">s</sub></span> 为小数（如 35% → 0.35）。
            </p>
          </template>
        </el-alert>

        <div class="footer-actions">
          <el-button
            type="primary"
            :loading="store.loading"
            :disabled="!store.sandRatioConfirmed || !store.vg || !store.rhog || !store.rhos"
            @click="handleNext"
          >
            下一步
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.el-table :deep(.is-selected-row td) {
  background: #e8f0fb !important;
  font-weight: 700;
}
</style>