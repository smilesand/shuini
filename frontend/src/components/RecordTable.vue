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
}>(), {
  loading: false,
  showProjectName: false,
  border: false,
})

const materialColumns: RecordColumnDefinition[] = [
  { key: 'mc', label: '水泥', digits: 1, width: 96 },
  { key: 'm1', label: '粉煤灰', digits: 1, width: 96 },
  { key: 'm2', label: '矿粉', digits: 1, width: 96 },
  { key: 'm3', label: '微珠', digits: 1, width: 96 },
  { key: 'm4', label: '硅灰', digits: 1, width: 96 },
  { key: 'ms', label: '细骨料', digits: 1, width: 104 },
  { key: 'mg', label: '粗骨料', digits: 1, width: 104 },
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

function getRecordCellNumber(record: RecordItem, key: string): number | null {
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
  // Try group-based calculation first
  const groups = getRecordObject(record, 'strengthGroups') || extractTrialValue(record, 'strengthGroups')
  const rawGroups = (record.record_data as any)?.trial_data?.inputs?.strengthGroups
    || (record.record_data as any)?.trial_data?.strengthGroups
  if (Array.isArray(rawGroups) && rawGroups.length > 0) {
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
    if (avgs.length > 0) {
      const overall = avgs.reduce((s, v) => s + v, 0) / avgs.length
      return `${overall.toFixed(1)} MPa`
    }
  }

  // Legacy fallback
  const trialVal = extractTrialValue(record, 'evalStrength28d')
  if (trialVal !== null) return `${trialVal.toFixed(1)} MPa`

  const fcu0 = getRecordNumber(record, 'fcu0')
  return fcu0 !== null ? `${fcu0.toFixed(1)} MPa` : '—'
}

function slumpDisplay(record: RecordItem): string {
  const evalSlump = extractTrialValue(record, 'evalSlump')
  if (evalSlump !== null) return `${evalSlump.toFixed(0)} mm`

  const slumpMeasured = extractTrialValue(record, 'slumpMeasured')
  if (slumpMeasured !== null) return `${slumpMeasured.toFixed(0)} mm`

  return '—'
}

function spreadDisplay(record: RecordItem): string {
  const evalSpread = extractTrialValue(record, 'evalSpread')
  if (evalSpread !== null) return `${evalSpread.toFixed(0)} mm`

  const spreadMeasured = extractTrialValue(record, 'spreadMeasured')
  if (spreadMeasured !== null) return `${spreadMeasured.toFixed(0)} mm`

  return '—'
}

function wbDisplay(record: RecordItem): string {
  const wb = getRecordNumber(record, 'wb')
  return wb !== null ? wb.toFixed(4) : '—'
}

function sandRatioDisplay(record: RecordItem): string {
  const sr = getRecordNumber(record, 'sand_ratio')
  return sr !== null ? `${sr.toFixed(1)} %` : '—'
}

function totalMassDisplay(record: RecordItem): string {
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
    <el-table-column label="类别" width="90" fixed="left" align="center">
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
  <el-empty v-else v-loading="loading" description="暂无配合记录" :image-size="88" />
</template>

<style scoped>
.record-table-wrap {
  width: 100%;
  overflow-x: auto;
}
</style>
