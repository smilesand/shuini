<script setup lang="ts">
import { computed } from 'vue'
import { getRecordData, getRecordNumber, getRecordObject, type RecordItem } from '../api/records'

interface RecordColumnDefinition {
  key: string
  label: string
  digits: number
  width: number
}

const props = withDefaults(defineProps<{
  records: RecordItem[]
  loading?: boolean
  showProjectName?: boolean
  getProjectName?: (record: RecordItem) => string
  border?: boolean
  emptyDescription?: string
  hideCategory?: boolean
}>(), {
  loading: false,
  showProjectName: false,
  border: false,
  emptyDescription: '暂无配合记录',
  hideCategory: false,
})

const materialColumns: RecordColumnDefinition[] = [
  { key: 'mc', label: '水泥', digits: 1, width: 96 },
  { key: 'm1', label: '粉煤灰', digits: 1, width: 96 },
  { key: 'm2', label: '矿粉', digits: 1, width: 96 },
  { key: 'm3', label: '微珠', digits: 1, width: 96 },
  { key: 'm4', label: '硅灰', digits: 1, width: 96 },
  { key: 'mg', label: '粗骨料', digits: 1, width: 104 },
  { key: 'ms', label: '细骨料', digits: 1, width: 104 },
  { key: 'mw', label: '水', digits: 1, width: 96 },
  { key: 'ma', label: '外加剂', digits: 1, width: 96 },
  { key: 'steel_fiber', label: '钢纤维', digits: 1, width: 104 },
]

const materialTotalWidth = computed(() =>
  materialColumns.reduce((sum, col) => sum + col.width, 0),
)

// ── Helpers ──

function fmtDate(value?: string | null) {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

function isRecordObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function toFiniteNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function getSteelFiberValue(record: RecordItem): number | null {
  const flatValue = toFiniteNumber(record.steel_fiber)
  if (flatValue !== null) return flatValue

  const recordData = getRecordData(record)
  const directValue = toFiniteNumber(recordData.steel_fiber)
  if (directValue !== null) return directValue

  const designData = isRecordObject(recordData.design_data) ? recordData.design_data : null
  const calculated = designData && isRecordObject(designData.calculated) ? designData.calculated : null
  const materialMasses = calculated && isRecordObject(calculated.materialMasses) ? calculated.materialMasses : null
  return materialMasses ? toFiniteNumber(materialMasses.steelFiber) : null
}

/**
 * 解析“配合比校正与确认”的最终实验室配合比。
 *
 * 配合比记录在 `record_data.trial_data` 中保存试配快照：
 *  - HPC 试配：`trial_data.calculated.labMix`（表观密度校正后的实验室配合比）优先，
 *    若未做密度校正则退回 `trial_data.calculated.adaptResult`（调整适配后的配合比）。
 *  - UHPC 试配：`trial_data.lab_mix` / `trial_data.labMix`（校正后的最终配合比）。
 * 统一映射为表格列键（mc/m1/m2/m3/m4/mg/ms/mw/ma/steel_fiber/total）。
 * 若记录没有试配数据，则返回 null，沿用 record_data 顶层的基准配合比。
 */
const FINAL_MIX_KEYS = ['mc', 'm1', 'm2', 'm3', 'm4', 'mg', 'ms', 'mw', 'ma', 'steel_fiber', 'total'] as const
type FinalMix = Record<(typeof FINAL_MIX_KEYS)[number], number | null>

const finalMixCache = new WeakMap<RecordItem, FinalMix | null>()

function buildFinalLabMix(record: RecordItem): FinalMix | null {
  const trial = getRecordObject(record, 'trial_data')
  if (!trial) return null

  // ── HPC 试配 ──
  const calculated = isRecordObject(trial.calculated) ? trial.calculated : null
  if (calculated) {
    const labMix = isRecordObject(calculated.labMix)
      ? calculated.labMix
      : isRecordObject(calculated.lab_mix)
        ? calculated.lab_mix
        : null
    const adaptResult = isRecordObject(calculated.adaptResult)
      ? calculated.adaptResult
      : isRecordObject(calculated.adapt_result)
        ? calculated.adapt_result
        : null
    const hpcMix =
      labMix && toFiniteNumber(labMix.mc) !== null ? labMix
        : adaptResult && toFiniteNumber(adaptResult.mc) !== null ? adaptResult
          : null
    if (hpcMix) {
      return {
        mc: toFiniteNumber(hpcMix.mc),
        m1: toFiniteNumber(hpcMix.m1),
        m2: toFiniteNumber(hpcMix.m2),
        m3: toFiniteNumber(hpcMix.m3),
        m4: toFiniteNumber(hpcMix.m4),
        mg: toFiniteNumber(hpcMix.mg),
        ms: toFiniteNumber(hpcMix.ms),
        mw: toFiniteNumber(hpcMix.mw),
        ma: toFiniteNumber(hpcMix.ma),
        steel_fiber: null,
        total: toFiniteNumber(hpcMix.total),
      }
    }
  }

  // ── UHPC 试配 ──
  const uhpcLab = isRecordObject(trial.lab_mix)
    ? trial.lab_mix
    : isRecordObject(trial.labMix)
      ? trial.labMix
      : null
  if (uhpcLab && (toFiniteNumber(uhpcLab.cement) !== null || toFiniteNumber(uhpcLab.mc) !== null)) {
    return {
      mc: toFiniteNumber(uhpcLab.cement) ?? toFiniteNumber(uhpcLab.mc),
      m1: toFiniteNumber(uhpcLab.fly_ash) ?? toFiniteNumber(uhpcLab.m1),
      m2: null,
      m3: toFiniteNumber(uhpcLab.micro_bead) ?? toFiniteNumber(uhpcLab.m3),
      m4: toFiniteNumber(uhpcLab.silica_fume) ?? toFiniteNumber(uhpcLab.m4),
      mg: null,
      ms: toFiniteNumber(uhpcLab.sand) ?? toFiniteNumber(uhpcLab.ms),
      mw: toFiniteNumber(uhpcLab.water) ?? toFiniteNumber(uhpcLab.mw),
      ma: toFiniteNumber(uhpcLab.admixture) ?? toFiniteNumber(uhpcLab.ma),
      steel_fiber: toFiniteNumber(uhpcLab.steel_fiber) ?? toFiniteNumber(uhpcLab.steelFiber),
      total: toFiniteNumber(uhpcLab.total),
    }
  }

  return null
}

function sumFinalMixMaterials(mix: FinalMix): number | null {
  const values = ['mc', 'm1', 'm2', 'm3', 'm4', 'mg', 'ms', 'mw', 'ma', 'steel_fiber']
    .map((key) => mix[key as keyof FinalMix])
    .filter((value): value is number => value !== null)
  if (values.length === 0) return null
  return values.reduce((sum, value) => sum + value, 0)
}

function resolveFinalLabMix(record: RecordItem): FinalMix | null {
  if (finalMixCache.has(record)) return finalMixCache.get(record) ?? null
  const mix = buildFinalLabMix(record)
  finalMixCache.set(record, mix)
  return mix
}

function getRecordCellNumber(record: RecordItem, key: string): number | null {
  const finalMix = resolveFinalLabMix(record)
  if (finalMix && (FINAL_MIX_KEYS as readonly string[]).includes(key)) {
    const finalValue = finalMix[key as keyof FinalMix]
    if (finalValue !== null) return finalValue
    // 最终配合比存在但该材料缺省（如 UHPC 无矿粉/粗骨料）：钢纤维另行回退，其余显示占位。
    if (key === 'steel_fiber') return getSteelFiberValue(record)
    return null
  }

  if (key === 'steel_fiber') return getSteelFiberValue(record)

  const storedValue = getRecordNumber(record, key)
  if (storedValue !== null) return storedValue

  return toFiniteNumber(record[key])
}

function formatRecordCell(record: RecordItem, key: string, digits = 1) {
  const value = getRecordCellNumber(record, key)
  return value !== null ? value.toFixed(digits) : '-'
}

function extractTrialValue(record: RecordItem, key: string): number | null {
  const trialData = getRecordObject(record, 'trial_data')
  if (!trialData) return null

  const inputs = trialData.inputs as Record<string, unknown> | undefined
  const val = inputs ? inputs[key] : trialData[key]
  if (typeof val === 'number' && Number.isFinite(val)) return val
  return null
}

function strength28dDisplay(record: RecordItem): string {
  // 强度总体平均值 — 仅来自配合比较正与确认的 strengthGroups
  const trialData = getRecordObject(record, 'trial_data')
  if (!trialData) return '—'

  const inputs = trialData.inputs as Record<string, unknown> | undefined
  const rawGroups = (inputs?.strengthGroups || trialData.strengthGroups) as { id: string; values: (number | null)[] }[] | undefined

  if (!Array.isArray(rawGroups) || rawGroups.length === 0) return '—'

  const avgs: number[] = []
  for (const g of rawGroups) {
    const vals = (Array.isArray(g.values) ? g.values : []).filter((v: unknown): v is number => typeof v === 'number' && Number.isFinite(v))
    if (vals.length < 3) continue
    const sorted = [...vals].sort((a: number, b: number) => a - b)
    const mean = (sorted[0] + sorted[1] + sorted[2]) / 3
    if (mean === 0) { avgs.push(0); continue }
    const maxDev = Math.abs((sorted[2] - mean) / mean)
    const minDev = Math.abs((sorted[0] - mean) / mean)
    if (maxDev > 0.15 || minDev > 0.15) {
      avgs.push(sorted[1])
    } else {
      avgs.push(mean)
    }
  }
  if (avgs.length === 0) return '—'
  const overall = avgs.reduce((s, v) => s + v, 0) / avgs.length
  return `${overall.toFixed(1)} MPa`
}

function slumpDisplay(record: RecordItem): string {
  // UHPC 使用 evalSlump，HPC 配合比校正与确认中使用 slumpMeasured
  const evalSlump = extractTrialValue(record, 'evalSlump')
  if (evalSlump !== null) return `${evalSlump.toFixed(0)} mm`

  const slumpMeasured = extractTrialValue(record, 'slumpMeasured')
  if (slumpMeasured !== null) return `${slumpMeasured.toFixed(0)} mm`

  return '—'
}

function spreadDisplay(record: RecordItem): string {
  // UHPC 使用 evalSpread，HPC 配合比校正与确认中使用 spreadMeasured
  const evalSpread = extractTrialValue(record, 'evalSpread')
  if (evalSpread !== null) return `${evalSpread.toFixed(0)} mm`

  const spreadMeasured = extractTrialValue(record, 'spreadMeasured')
  if (spreadMeasured !== null) return `${spreadMeasured.toFixed(0)} mm`

  return '—'
}

function wbDisplay(record: RecordItem): string {
  // 强度实验回归分析的最终推荐水胶比
  const wbAdj = extractTrialValue(record, 'wbAdj')
  if (wbAdj !== null) return wbAdj.toFixed(2)

  const wb = getRecordNumber(record, 'wb')
  return wb !== null ? wb.toFixed(2) : '—'
}

function sandRatioDisplay(record: RecordItem): string {
  // 强度实验回归分析的最终推荐砂率
  const srAdj = extractTrialValue(record, 'sandRatioAdj')
  if (srAdj !== null) return `${srAdj.toFixed(1)} %`

  const sr = getRecordNumber(record, 'sand_ratio')
  return sr !== null ? `${sr.toFixed(1)} %` : '—'
}

function totalMassDisplay(record: RecordItem): string {
  const finalMix = resolveFinalLabMix(record)
  if (finalMix) {
    const total = finalMix.total ?? sumFinalMixMaterials(finalMix)
    return total !== null ? total.toFixed(0) : '—'
  }
  const total = getRecordNumber(record, 'total_mass')
  return total !== null ? total.toFixed(0) : '—'
}

function categoryTag(cat: string): 'primary' | 'warning' | 'success' | 'info' {
  if (cat === 'uhpc' || cat === 'uhpc_trial') return 'warning'
  if (cat === 'hpc_trial') return 'success'
  return 'primary'
}

function categoryLabel(cat: string) {
  if (cat === 'uhpc') return 'UHPC'
  if (cat === 'hpc') return 'HPC'
  if (cat === 'hpc_trial') return 'HPC试配'
  if (cat === 'uhpc_trial') return 'UHPC试配'
  return cat
}
</script>

<template>
  <div v-if="records.length" v-loading="loading" class="record-table-wrap">
    <el-table
      :data="records"
      :border="border"
      :stripe="!border"
      size="small"
      style="width: 100%"
    >
    <el-table-column
      v-if="showProjectName"
      label="项目名称"
      width="180"
      fixed="left"
      show-overflow-tooltip
    >
      <template #default="{ row }">
        {{ getProjectName ? getProjectName(row) : '—' }}
      </template>
    </el-table-column>
    <el-table-column prop="name" label="配比名称" width="180" fixed="left" show-overflow-tooltip />
    <el-table-column v-if="!hideCategory" label="类别" width="90" fixed="left" align="center">
      <template #default="{ row }">
        <el-tag :type="categoryTag(row.category)" size="small">
          {{ categoryLabel(row.category) }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="配合比材料" :width="materialTotalWidth" align="center">
      <el-table-column
        v-for="column in materialColumns"
        :key="column.key"
        :label="column.label"
        :width="column.width"
        align="center"
      >
        <template #default="{ row }">{{ formatRecordCell(row, column.key, column.digits) }}</template>
      </el-table-column>
    </el-table-column>
    <el-table-column label="28d抗压强度" width="130" align="center">
      <template #default="{ row }">{{ strength28dDisplay(row) }}</template>
    </el-table-column>
    <el-table-column label="实测坍落度" width="110" align="center">
      <template #default="{ row }">{{ slumpDisplay(row) }}</template>
    </el-table-column>
    <el-table-column label="实测扩展度" width="110" align="center">
      <template #default="{ row }">{{ spreadDisplay(row) }}</template>
    </el-table-column>
    <el-table-column label="水胶比" width="100" align="center">
      <template #default="{ row }">{{ wbDisplay(row) }}</template>
    </el-table-column>
    <el-table-column label="砂率" width="90" align="center">
      <template #default="{ row }">{{ sandRatioDisplay(row) }}</template>
    </el-table-column>
    <el-table-column label="总量" width="90" align="center">
      <template #default="{ row }">{{ totalMassDisplay(row) }}</template>
    </el-table-column>
    <el-table-column prop="created_by" label="创建人" width="110" align="center" fixed="right" />
    <el-table-column label="时间" width="170" align="center" fixed="right">
      <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
    </el-table-column>
    <el-table-column label="操作" width="160" fixed="right" align="center">
      <template #default="{ row, $index }">
        <slot name="actions" :row="row" :index="$index" />
      </template>
    </el-table-column>
  </el-table>
  </div>
  <el-empty v-else v-loading="loading" :description="emptyDescription" :image-size="88" />
</template>

<style scoped>
.record-table-wrap {
  width: 100%;
  overflow-x: auto;
}
</style>
