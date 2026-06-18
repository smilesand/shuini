<script setup lang="ts">
import { computed } from 'vue'

interface HpcTrialDataTableColumn {
  key: string
  label: string
  width?: number | string
  minWidth?: number | string
}

interface HpcTrialDataTableCell {
  text: string
  unit?: string
  changed?: boolean
  emphasized?: boolean
  /** When set, renders an el-input-number instead of plain text */
  input?: {
    value: number | null
    onInput: (v: number | null) => void
    min?: number
    max?: number
    step?: number
    precision?: number
    placeholder?: string
  }
}

type HpcTrialDataTableValue = HpcTrialDataTableCell | string | number | null | undefined
type HpcTrialDataTableRow = Record<string, HpcTrialDataTableValue>

const props = withDefaults(defineProps<{
  columns: HpcTrialDataTableColumn[]
  rows: HpcTrialDataTableRow[]
  variant?: string
}>(), {
  variant: 'default',
})

const tableClass = computed(() => `materials-table--${props.variant}`)

function isCellObject(value: HpcTrialDataTableValue): value is HpcTrialDataTableCell {
  return typeof value === 'object' && value !== null && 'text' in value
}

function getCellText(value: HpcTrialDataTableValue) {
  if (value === null || value === undefined) {
    return '—'
  }
  return isCellObject(value) ? value.text : String(value)
}

function getCellUnit(value: HpcTrialDataTableValue) {
  return isCellObject(value) ? value.unit : undefined
}

function getCellInput(value: HpcTrialDataTableValue) {
  return isCellObject(value) ? value.input : undefined
}

function resolveCellClassName({ row, column }: { row: HpcTrialDataTableRow; column: { property?: string } }) {
  const key = column.property
  if (!key) return ''
  const value = row[key]
  if (!isCellObject(value)) return ''
  return [
    value.changed ? 'is-changed' : '',
    value.emphasized ? 'is-emphasized' : '',
    value.unit || value.input ? 'has-unit' : '',
  ].filter(Boolean).join(' ')
}
</script>

<template>
  <div class="materials-table-wrap">
    <el-table
      :data="rows"
      border
      size="small"
      table-layout="fixed"
      class="materials-table"
      :class="tableClass"
      :cell-class-name="resolveCellClassName"
    >
      <el-table-column
        v-for="column in columns"
        :key="column.key"
        :prop="column.key"
        :label="column.label"
        :width="column.width"
        :min-width="column.minWidth ?? 82"
        align="center"
      >
        <template #default="{ row }">
          <template v-if="getCellInput(row[column.key])">
            <el-input-number
              :model-value="getCellInput(row[column.key])!.value ?? undefined"
              @update:model-value="v => getCellInput(row[column.key])!.onInput(v ?? null)"
              :min="getCellInput(row[column.key])!.min ?? 0"
              :max="getCellInput(row[column.key])!.max ?? 100"
              :step="getCellInput(row[column.key])!.step ?? 0.1"
              :precision="getCellInput(row[column.key])!.precision ?? 2"
              :placeholder="getCellInput(row[column.key])!.placeholder ?? ''"
              size="small"
              controls-position="right"
              style="width:100%"
            />
          </template>
          <template v-else-if="getCellUnit(row[column.key])">
            <div class="trial-cell">
              <span class="trial-val">{{ getCellText(row[column.key]) }}</span>
              <span class="trial-unit">{{ getCellUnit(row[column.key]) }}</span>
            </div>
          </template>
          <span v-else class="trial-table-text">{{ getCellText(row[column.key]) }}</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>