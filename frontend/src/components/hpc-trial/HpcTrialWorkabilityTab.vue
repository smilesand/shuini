<script setup lang="ts">
import { computed } from 'vue'
import HpcTrialDataTable from './HpcTrialDataTable.vue'
import { useHpcTrialContext } from '../../composables/context'
import { formatNullableNumber } from '../../utils/format'
import '../../style/calc-tabs.css'

const trial = useHpcTrialContext()
const {
  hasData,
  mcVal,
  m1Val,
  m2Val,
  m3Val,
  m4Val,
  mgVal,
  msVal,
  mwVal,
  maVal,
  mbVal,
  sandRatioVal,
  alphaVal,
  wbVal,
  batchVolume,
  workabilityBinderDelta,
  workabilitySandRatioDelta,
  workabilityAlphaDelta,
  slumpMeasured,
  spreadMeasured,
  selectedWorkabilityReference,
  workabilityEvaluation,
  workabilityNote,
  trialMatCols,
  workabilityResult,
  resetWorkability,
} = trial

const fmt = formatNullableNumber

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
]

interface WorkabilityTableCell {
  text: string
  unit?: string
  changed?: boolean
  emphasized?: boolean
}

interface WorkabilityMixRow {
  rowKey: 'per-cubic' | 'trial-batch'
  trialVolume: WorkabilityTableCell
  [key: string]: WorkabilityTableCell | string
}

function createTableCell(value: number | null | undefined, digits = 2, options: {
  unit?: string
  changed?: boolean
  emphasized?: boolean
} = {}) {
  return {
    text: fmt(value, digits),
    unit: options.unit,
    changed: options.changed,
    emphasized: options.emphasized,
  }
}

function isCellObject(value: unknown): value is WorkabilityTableCell {
  return typeof value === 'object' && value !== null && 'text' in value
}

function getCellText(value: unknown) {
  if (value === null || value === undefined) {
    return '—'
  }

  return isCellObject(value) ? value.text : String(value)
}

function getCellUnit(value: unknown) {
  return isCellObject(value) ? value.unit : undefined
}

function resolveMergedCellClassName({ row, column }: { row: WorkabilityMixRow; column: { property?: string } }) {
  const key = column.property

  if (!key || key === 'rowKey') {
    return ''
  }

  if (key === 'trialVolume' && row.rowKey === 'trial-batch') {
    return 'is-editable-cell'
  }

  const value = row[key]
  if (!isCellObject(value)) {
    return ''
  }

  return [
    value.changed ? 'is-changed' : '',
    value.emphasized ? 'is-emphasized' : '',
    value.unit ? 'has-unit' : '',
  ].filter(Boolean).join(' ')
}

const binderDeltaMin = computed(() => (
  mbVal.value !== null ? -mbVal.value + 1 : -999
))

const sandRatioDeltaMin = computed(() => (
  sandRatioVal.value !== null ? -sandRatioVal.value + 0.01 : -99
))

const sandRatioDeltaMax = computed(() => (
  sandRatioVal.value !== null ? 99.99 - sandRatioVal.value : 99
))

const alphaDeltaMin = computed(() => (
  alphaVal.value !== null ? -alphaVal.value : -20
))

const baseMaterialRows = computed(() => ([{
  mc: createTableCell(mcVal.value),
  m1: createTableCell(m1Val.value),
  m2: createTableCell(m2Val.value),
  m3: createTableCell(m3Val.value),
  m4: createTableCell(m4Val.value),
  mg: createTableCell(mgVal.value),
  ms: createTableCell(msVal.value),
  mw: createTableCell(mwVal.value),
  ma: createTableCell(maVal.value),
}]))

const trialBatchMap = computed(() => trialMatCols.value.reduce<Record<string, number | null>>((row, column) => {
  row[column.key] = column.trialVal
  return row
}, {}))

const mergedMixRows = computed<WorkabilityMixRow[]>(() => {
  const binderChanged = workabilityBinderDelta.value !== 0
  const sandChanged = workabilitySandRatioDelta.value !== 0
  const alphaChanged = workabilityAlphaDelta.value !== 0
  const trialBatch = trialBatchMap.value

  return [{
    rowKey: 'per-cubic',
    trialVolume: createTableCell(1000, 0, { unit: 'L', emphasized: true }),
    mc: createTableCell(workabilityResult.value.mc, 2, { changed: binderChanged }),
    m1: createTableCell(workabilityResult.value.m1, 2, { changed: binderChanged }),
    m2: createTableCell(workabilityResult.value.m2, 2, { changed: binderChanged }),
    m3: createTableCell(workabilityResult.value.m3, 2, { changed: binderChanged }),
    m4: createTableCell(workabilityResult.value.m4, 2, { changed: binderChanged }),
    mg: createTableCell(workabilityResult.value.mg, 2),
    ms: createTableCell(workabilityResult.value.ms, 2, { changed: sandChanged }),
    mw: createTableCell(workabilityResult.value.mw, 2, { changed: binderChanged }),
    ma: createTableCell(workabilityResult.value.ma, 2, { changed: binderChanged || alphaChanged }),
  }, {
    rowKey: 'trial-batch',
    trialVolume: createTableCell(batchVolume.value, 0, { unit: 'L', emphasized: true }),
    mc: createTableCell(trialBatch.mc, 3, { changed: binderChanged }),
    m1: createTableCell(trialBatch.m1, 3, { changed: binderChanged }),
    m2: createTableCell(trialBatch.m2, 3, { changed: binderChanged }),
    m3: createTableCell(trialBatch.m3, 3, { changed: binderChanged }),
    m4: createTableCell(trialBatch.m4, 3, { changed: binderChanged }),
    mg: createTableCell(trialBatch.mg, 3),
    ms: createTableCell(trialBatch.ms, 3, { changed: sandChanged }),
    mw: createTableCell(trialBatch.mw, 3, { changed: binderChanged }),
    ma: createTableCell(trialBatch.ma, 3, { changed: binderChanged || alphaChanged }),
  }]
})

</script>

<template>
  <div>
    <el-alert
      v-if="!hasData"
      title="请先在配比计算 → 高性能混凝土中完成配合比计算，之后再回到本页进行工作性实验。"
      type="warning"
      show-icon
      :closable="false"
      style="margin-bottom: 16px"
    />

    <template v-else>
      <!-- 计算配合比 -->
      <div class="cs-section">
        <div class="cs-section-head">
          <el-icon><List /></el-icon>
          计算配合比（每方用量）
        </div>
        <div class="cs-section-body">
          <HpcTrialDataTable :columns="materialColumns" :rows="baseMaterialRows" />
        </div>
      </div>

      <!-- 调整变量 -->
      <div class="cs-section">
        <div class="cs-section-head">
          <el-icon><Setting /></el-icon>
          基础调整变量
        </div>
        <div class="cs-section-body">
          <p class="trial-adjust-note">
            水胶比 W/B 固定为 {{ fmt(wbVal, 4) }}。下列三个基准量不可直接修改，通过右侧增减量重算工作性试拌配合比。
          </p>
          <el-form label-position="top" size="default">
            <el-row :gutter="20">
              <el-col :span="8">
                <el-form-item>
                  <template #label>胶材用量 m<sub>b</sub></template>
                  <div class="trial-adjust-control">
                    <el-input :model-value="fmt(mbVal)" readonly class="trial-readonly-input">
                      <template #suffix><span class="unit-suffix">kg/m³</span></template>
                    </el-input>
                    <el-input-number
                      v-model="workabilityBinderDelta"
                      :step="5"
                      :precision="2"
                      :min="binderDeltaMin"
                      style="width: 100%"
                    >
                      <template #suffix><span class="unit-suffix">Δkg</span></template>
                    </el-input-number>
                  </div>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item>
                  <template #label>砂率 β<sub>s</sub></template>
                  <div class="trial-adjust-control">
                    <el-input :model-value="fmt(sandRatioVal)" readonly class="trial-readonly-input">
                      <template #suffix><span class="unit-suffix">%</span></template>
                    </el-input>
                    <el-input-number
                      v-model="workabilitySandRatioDelta"
                      :step="0.5"
                      :precision="2"
                      :min="sandRatioDeltaMin"
                      :max="sandRatioDeltaMax"
                      style="width: 100%"
                    >
                      <template #suffix><span class="unit-suffix">Δ%</span></template>
                    </el-input-number>
                  </div>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item>
                  <template #label>外加剂掺量 α</template>
                  <div class="trial-adjust-control">
                    <el-input :model-value="fmt(alphaVal)" readonly class="trial-readonly-input">
                      <template #suffix><span class="unit-suffix">%</span></template>
                    </el-input>
                    <el-input-number
                      v-model="workabilityAlphaDelta"
                      :step="0.05"
                      :precision="2"
                      :min="alphaDeltaMin"
                      style="width: 100%"
                    >
                      <template #suffix><span class="unit-suffix">Δ%</span></template>
                    </el-input-number>
                  </div>
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </div>
      </div>

      <!-- 试拌配合比 -->
      <div class="cs-section">
        <div class="cs-section-head">
          <el-icon><Grid /></el-icon>
          试拌配合比
        </div>
        <div class="cs-section-body">
          <p style="font-size: 12px; color: #909399; margin: 0 0 10px">调整后试拌配合比与试拌用量</p>
          <div class="materials-table-wrap">
            <el-table
              :data="mergedMixRows"
              border
              size="small"
              table-layout="fixed"
              class="materials-table materials-table--workability-merged"
              :cell-class-name="resolveMergedCellClassName"
            >
              <el-table-column prop="trialVolume" label="试拌体积" :min-width="120" align="center" fixed="left">
                <template #default="{ row }">
                  <div v-if="row.rowKey === 'trial-batch'" class="trial-volume-cell">
                    <el-input-number
                      v-model="batchVolume"
                      :min="1"
                      :max="100"
                      :step="5"
                      style="width: 100%"
                    >
                      <template #suffix><span class="unit-suffix">L</span></template>
                    </el-input-number>
                  </div>
                  <div v-else class="trial-cell">
                    <span class="trial-val">{{ getCellText(row.trialVolume) }}</span>
                    <span v-if="getCellUnit(row.trialVolume)" class="trial-unit">{{ getCellUnit(row.trialVolume) }}</span>
                  </div>
                </template>
              </el-table-column>

              <el-table-column
                v-for="column in materialColumns"
                :key="column.key"
                :prop="column.key"
                :label="column.label"
                :min-width="82"
                align="center"
              >
                <template #default="{ row }">
                  <div v-if="getCellUnit(row[column.key])" class="trial-cell">
                    <span class="trial-val">{{ getCellText(row[column.key]) }}</span>
                    <span class="trial-unit">{{ getCellUnit(row[column.key]) }}</span>
                  </div>
                  <span v-else class="trial-table-text">{{ getCellText(row[column.key]) }}</span>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div class="formula-row" style="margin-top: 6px">
            <span class="formula-label">固定 W/B：</span>
            <span class="formula-val">{{ fmt(workabilityResult.wb, 4) }}</span>
            <span class="formula-label" style="margin-left: 20px">调整后 m<sub>b</sub>：</span>
            <span class="formula-val" :class="{ changed: workabilityBinderDelta !== 0 }">{{ fmt(workabilityResult.mb) }} kg/m³</span>
            <span class="formula-label" style="margin-left: 20px">调整后 β<sub>s</sub>：</span>
            <span class="formula-val" :class="{ changed: workabilitySandRatioDelta !== 0 }">{{ fmt(workabilityResult.bs) }} %</span>
            <span class="formula-label" style="margin-left: 20px">调整后 α：</span>
            <span class="formula-val" :class="{ changed: workabilityAlphaDelta !== 0 }">{{ fmt(workabilityResult.alpha) }} %</span>
          </div>
        </div>
      </div>

      <!-- 合计说明 -->
      <div class="cs-section">
        <div class="cs-section-body" style="padding-top: 0;">
          <div class="total-card">
            <span class="total-label">调整后每方合计</span>
            <span class="total-val">{{ workabilityResult.total ? workabilityResult.total.toFixed(2) + ' kg/m³' : '—' }}</span>
          </div>

          <el-alert type="info" :closable="false" style="margin-top: 12px">
            <template #title>工作性实验说明</template>
            <template #default>
              <p style="margin: 0; line-height: 1.8; font-size: 12px">
                先以设计配合比为基准，保持水胶比不变，通过调整胶材用量、砂率和外加剂掺量重算每方配合比，
                其中调整砂率时保持粗骨料与细骨料总量不变，按目标砂率重新分配粗细骨料，
                再按试拌体积换算各材料试拌用量。确认工作性满足目标后，点击页面下方"下一步"即可进入强度实验。
              </p>
            </template>
          </el-alert>
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
</style>
