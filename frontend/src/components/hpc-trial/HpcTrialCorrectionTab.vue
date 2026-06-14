<script setup lang="ts">
import { computed } from 'vue'
import HpcTrialDataTable from './HpcTrialDataTable.vue'
import { useHpcTrialContext } from '../../composables/context'
import { formatNullableNumber } from '../../utils/format'
import '../../style/calc-tabs.css'

const {
  hasData,
  adaptResult,
  measuredDensity,
  calculatedDensity,
  densityCorrectionFactor,
  labMix,
  resetCorrection,
  evalStrength28d,
  slumpMeasured,
  spreadMeasured,
  workabilityNote,
  workabilityEvaluation,
  strengthEvaluation,
  selectedWorkabilityReference,
} = useHpcTrialContext()

const fmt = formatNullableNumber

// 密度偏差判断（与 UHPC 一致：偏差 > 2% 则需校正）
const densityDeviation = computed(() => {
  const m = measuredDensity.value
  const c = calculatedDensity.value
  if (m == null || c == null || c === 0) return null
  return Math.abs((m - c) / c) * 100
})

const needsCorr = computed(() => {
  const d = densityDeviation.value
  return d !== null && d > 2
})

const materialColumns = [
  { key: 'mc', label: '水泥' },
  { key: 'm1', label: '粉煤灰' },
  { key: 'm2', label: '矿粉' },
  { key: 'm3', label: '微珠' },
  { key: 'm4', label: '硅灰' },
  { key: 'mg', label: '粗骨料' },
  { key: 'ms', label: '细骨料' },
  { key: 'mw', label: '水' },
  { key: 'ma', label: '外加剂' },
  { key: 'total', label: '合计' },
]

function createTableCell(value: number | null | undefined, digits = 2, options: {
  emphasized?: boolean
} = {}) {
  return {
    text: fmt(value, digits),
    emphasized: options.emphasized,
  }
}

const adaptResultRows = computed(() => ([{
  mc: createTableCell(adaptResult.value.mc),
  m1: createTableCell(adaptResult.value.m1),
  m2: createTableCell(adaptResult.value.m2),
  m3: createTableCell(adaptResult.value.m3),
  m4: createTableCell(adaptResult.value.m4),
  mg: createTableCell(adaptResult.value.mg),
  ms: createTableCell(adaptResult.value.ms),
  mw: createTableCell(adaptResult.value.mw),
  ma: createTableCell(adaptResult.value.ma),
  total: createTableCell(adaptResult.value.total, 2, { emphasized: true }),
}]))

const labMixRows = computed(() => ([{
  mc: createTableCell(labMix.value.mc),
  m1: createTableCell(labMix.value.m1),
  m2: createTableCell(labMix.value.m2),
  m3: createTableCell(labMix.value.m3),
  m4: createTableCell(labMix.value.m4),
  mg: createTableCell(labMix.value.mg),
  ms: createTableCell(labMix.value.ms),
  mw: createTableCell(labMix.value.mw),
  ma: createTableCell(labMix.value.ma),
  total: createTableCell(labMix.value.total, 2, { emphasized: true }),
}]))

</script>

<template>
  <div>
    <el-alert
      v-if="!hasData"
      title="请先在配比计算 → 高性能混凝土中完成配合比计算，之后再回到本页进行试配调整。"
      type="warning"
      show-icon
      :closable="false"
      style="margin-bottom: 16px"
    />

    <template v-else>
      <!-- 调整配合比 -->
      <div class="cs-section">
        <div class="cs-section-head">
          <el-icon><Edit /></el-icon>
          调整配合比（来自强度实验调整结果）
        </div>
        <div class="cs-section-body">
          <p style="font-size: 12px; color: #909399; margin: 0 0 10px">
            本页直接承接前一步根据推荐水胶比生成的最终配合比结果，并继续进行表观密度校正与实验室配合比确认。
          </p>
          <HpcTrialDataTable :columns="materialColumns" :rows="adaptResultRows" variant="trial-adjust" />
        </div>
      </div>

      <!-- 表观密度校正 -->
      <div class="cs-section">
        <div class="cs-section-head">
          <el-icon><Odometer /></el-icon>
          表观密度校正
        </div>
        <div class="cs-section-body">
          <p style="font-size: 12px; color: #909399; margin: 0 0 12px">
            测定拌合物表观密度后，按校正系数 δ = ρ<sub>c,t</sub> / ρ<sub>c,c</sub> 修正实验室配合比，各组分比例保持不变。
          </p>
          <el-form label-position="top" size="default">
            <el-row :gutter="20">
              <el-col :span="6">
                <el-form-item>
                  <template #label>实测表观密度 ρ<sub>c,t</sub></template>
                  <el-input-number v-model="measuredDensity" :min="1000" :max="3000" :step="1" :precision="0" style="width: 100%">
                    <template #suffix><span class="unit-suffix">kg/m³</span></template>
                  </el-input-number>
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item>
                  <template #label>计算表观密度 ρ<sub>c,c</sub></template>
                  <el-input :value="calculatedDensity ? calculatedDensity.toFixed(2) : '—'" readonly class="computed-input">
                    <template #suffix><span class="unit-suffix">kg/m³</span></template>
                  </el-input>
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item>
                  <template #label>校正系数 δ</template>
                  <el-input :value="densityCorrectionFactor ? densityCorrectionFactor.toFixed(6) : '—'" readonly class="computed-input" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>

          <div
            v-if="densityCorrectionFactor !== null"
            class="corr-status"
            :class="needsCorr ? 'corr-status--warn' : 'corr-status--ok'"
          >
            <el-icon :size="16">
              <component :is="needsCorr ? 'Warning' : 'CircleCheck'" />
            </el-icon>
            <span v-if="needsCorr">
              偏差 {{ densityDeviation?.toFixed(2) }}% 已超过 2%，实验室配合比已乘以校正系数
              <b>δ = {{ densityCorrectionFactor.toFixed(6) }}</b>。
            </span>
            <span v-else>
              偏差 {{ densityDeviation?.toFixed(2) }}% 未超过 2%，实验室配合比维持调整配合比不变。
            </span>
          </div>
        </div>
      </div>

      <!-- 实验室配合比 -->
      <div class="cs-section">
        <div class="cs-section-head">
          <el-icon><DocumentChecked /></el-icon>
          实验室配合比
        </div>
        <div class="cs-section-body">
          <p style="font-size: 12px; color: #909399; margin: 0 0 10px">
            调整配合比各材料用量 × δ，保持目标水胶比不变。
          </p>
          <div style="display: flex; gap: 8px; margin-bottom: 14px">
            <el-button size="small" type="default" @click="resetCorrection">
              <el-icon><RefreshLeft /></el-icon>
              重置校正
            </el-button>
          </div>
          <HpcTrialDataTable :columns="materialColumns" :rows="labMixRows" variant="lab-mix" />

          <div v-if="densityCorrectionFactor" class="total-card">
            <span class="total-label">实验室配合比每方合计</span>
            <span class="total-val">{{ labMix.total ? labMix.total.toFixed(2) + ' kg/m³' : '—' }}</span>
          </div>

          <el-alert type="info" :closable="false" style="margin-top: 14px">
            <template #title>校正说明</template>
            <template #default>
              <p style="margin: 0; line-height: 1.8; font-size: 12px">
                当拌合物表观密度实测值与计算值偏差较大时，应按校正系数 δ 对实验室配合比进行统一放大或缩小，
                以保证后续试验配比与实测状态一致。
              </p>
            </template>
          </el-alert>
        </div>
      </div>

      <!-- 工作性与性能评价 (HPC) -->
      <div class="cs-section">
        <div class="cs-section-head">
          <el-icon><DataAnalysis /></el-icon>
          混凝土性能及评价（实验室配合比）
        </div>
        <div class="cs-section-body">
          <el-form label-position="top" size="default">
            <el-row :gutter="20">
              <el-col :span="8">
                <el-form-item>
                  <template #label>28d抗压强度</template>
                  <el-input-number
                    v-model="evalStrength28d"
                    :min="0" :max="400" :step="1" :precision="1"
                    placeholder="如 65"
                    style="width: 100%"
                  >
                    <template #suffix><span class="unit-suffix">MPa</span></template>
                  </el-input-number>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item>
                  <template #label>实测坍落度</template>
                  <el-input-number
                    v-model="slumpMeasured"
                    :min="0"
                    :max="300"
                    :step="5"
                    placeholder="如 180"
                    style="width: 100%"
                  >
                    <template #suffix><span class="unit-suffix">mm</span></template>
                  </el-input-number>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item>
                  <template #label>实测扩展度</template>
                  <el-input-number
                    v-model="spreadMeasured"
                    :min="0"
                    :max="900"
                    :step="5"
                    placeholder="如 650"
                    style="width: 100%"
                  >
                    <template #suffix><span class="unit-suffix">mm</span></template>
                  </el-input-number>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="20">
              <el-col :span="24">
                <el-form-item>
                  <template #label>工作性综合描述</template>
                  <el-input
                    v-model="workabilityNote"
                    type="textarea"
                    :rows="2"
                    placeholder="如：拌合物粘聚性良好，无离析泌水现象..."
                  />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="24">
                <div class="trial-workability-evaluation" style="display:flex;align-items:center;gap:12px;">
                  <span class="trial-workability-evaluation__label" style="font-weight:bold;color:#374151;">性能评价：</span>
                  <el-tag :type="workabilityEvaluation.tagType" size="small">{{ workabilityEvaluation.label }}</el-tag>
                  <span class="trial-workability-evaluation__detail" style="font-size:12px;color:#6b7280;">
                    {{ selectedWorkabilityReference ? workabilityEvaluation.detail : '请先在"骨料用量"中选择 Vg 参考范围。' }}
                  </span>
                  <el-tag :type="strengthEvaluation.tagType" size="small">{{ strengthEvaluation.label }}</el-tag>
                  <span class="trial-workability-evaluation__detail" style="font-size:12px;color:#6b7280;">
                    {{ strengthEvaluation.detail }}
                  </span>
                </div>
              </el-col>
            </el-row>
          </el-form>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.total-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 14px;
  padding: 14px 18px;
  border-radius: 10px;
  background: linear-gradient(135deg, #1e3c72, #2a5298);
  color: #fff;
}
.total-label { font-size: 14px; font-weight: 600; }
.total-val { font-size: 22px; font-weight: 800; }

/* ── Correction status ────────────────────────────────────────── */
.corr-status {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.6;
  margin-top: 12px;
}
.corr-status--warn {
  background: #fff3cd;
  border: 1px solid #f5c842;
  color: #856404;
}
.corr-status--ok {
  background: #d1e7dd;
  border: 1px solid #82c88a;
  color: #0f5132;
}
</style>
