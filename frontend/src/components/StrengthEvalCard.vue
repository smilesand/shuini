<script setup lang="ts">
import { computed } from 'vue'
import type { StrengthGroup } from '../composables/useStrengthEval'
import { computeGroupValue } from '../composables/useStrengthEval'

const props = defineProps<{
  groups: StrengthGroup[]
  targetStrength: number | null   // 配制强度 fcu,0
  strengthGrade: number | null    // 强度等级数值 (e.g., 80)
  /** 总平均抗压强度倍数：HPC=1.15, UHPC=1.10 */
  strengthMultiplier?: number
  readonly?: boolean
}>()

const multiplier = computed(() => props.strengthMultiplier ?? 1.15)

const emit = defineEmits<{
  (e: 'update:groups', v: StrengthGroup[]): void
}>()

// ── Group CRUD ──────────────────────────────────────────────────
let nextId = 1
function newId(): string {
  return `G${String(nextId++).padStart(2, '0')}`
}

function addGroup() {
  const updated = [...props.groups, { id: newId(), values: [null, null, null] as (number | null)[] }]
  emit('update:groups', updated)
}

function removeGroup(index: number) {
  if (props.groups.length <= 6) return
  const updated = props.groups.filter((_, i) => i !== index)
  emit('update:groups', updated)
}

function updateValue(groupIdx: number, valueIdx: number, raw: string | number | null | undefined) {
  const updated = props.groups.map((g, gi) => {
    if (gi !== groupIdx) return g
    const newValues = [...g.values]
    if (typeof raw === 'string') {
      const n = parseFloat(raw)
      newValues[valueIdx] = Number.isFinite(n) ? n : null
    } else {
      newValues[valueIdx] = raw ?? null
    }
    return { ...g, values: newValues }
  })
  emit('update:groups', updated)
}

// ── Per-group calculation ───────────────────────────────────────
interface GroupEval {
  value: number | null
  trimmed: boolean
  invalid: boolean
  trimmedIndices: number[]
  allFilled: boolean
}

const groupEvals = computed<GroupEval[]>(() =>
  props.groups.map(g => {
    const filled = g.values.filter(v => v !== null && Number.isFinite(v)).length
    const result = computeGroupValue(g.values)
    return {
      value: result.value,
      trimmed: result.trimmed,
      invalid: result.invalid,
      trimmedIndices: result.trimmedIndices,
      allFilled: filled === 3,
    }
  }),
)

// ── Overall statistics ──────────────────────────────────────────
const overallAvg = computed<number | null>(() => {
  const vals = groupEvals.value
    .filter(e => !e.invalid)
    .map(e => e.value)
    .filter((v): v is number => v !== null)
  if (vals.length === 0) return null
  return vals.reduce((s, v) => s + v, 0) / vals.length
})

const minGroupAvg = computed<number | null>(() => {
  const vals = groupEvals.value
    .filter(e => !e.invalid)
    .map(e => e.value)
    .filter((v): v is number => v !== null)
  if (vals.length === 0) return null
  return Math.min(...vals)
})

const allComplete = computed(() =>
  groupEvals.value.length >= 6
  && groupEvals.value.every(e => e.allFilled)
  && !groupEvals.value.some(e => e.invalid),
)

const hasInvalidGroups = computed(() =>
  groupEvals.value.some(e => e.invalid),
)

// ── Evaluation ──────────────────────────────────────────────────
const evaluation = computed(() => {
  const ov = overallAvg.value
  const minG = minGroupAvg.value
  const sg = props.strengthGrade

  if (!allComplete.value || ov === null) {
    const reason = hasInvalidGroups.value
      ? '存在无效试验组（最大值和最小值与中间值的差值均超过中间值的15%），请修正数据。'
      : '请完成所有 6 组（每组 3 条）强度数据填写。'
    return {
      status: 'pending' as const,
      label: '待评价',
      tagType: 'info' as const,
      detail: reason,
    }
  }

  // 六组试块强度平均值 ≥ multiplier × 强度等级
  const avgThreshold = sg !== null ? sg * multiplier.value : null
  const overallPass = avgThreshold !== null ? ov >= avgThreshold : null

  // 最小值 ≥ 0.95 × 强度等级
  const minThreshold = sg !== null ? sg * 0.95 : null
  const minGroupPass = minThreshold !== null && minG !== null ? minG >= minThreshold : null

  const allPass = overallPass !== false && (minGroupPass !== false)

  // Build detail message
  const parts: string[] = []
  const multLabel = multiplier.value.toFixed(2)

  if (avgThreshold !== null) {
    if (overallPass === false) {
      parts.push(`总体平均值 ${ov.toFixed(1)} MPa 不足 ${multLabel}×强度等级(${avgThreshold.toFixed(1)} MPa)，差值 ${(avgThreshold - ov).toFixed(1)} MPa`)
    }
  }

  if (minThreshold !== null && minG !== null && minGroupPass === false) {
    parts.push(`组均值最小值 ${minG.toFixed(1)} MPa 不足 0.95×强度等级(${minThreshold.toFixed(1)} MPa)，差值 ${(minThreshold - minG).toFixed(1)} MPa`)
  }

  if (allPass) {
    parts.unshift(`总体平均值 ${ov.toFixed(1)} MPa ≥ ${multLabel}×强度等级(${avgThreshold!.toFixed(1)} MPa)，组均值最小值 ${minG!.toFixed(1)} MPa ≥ 0.95×强度等级(${minThreshold!.toFixed(1)} MPa)`)
  }

  return {
    status: allPass ? ('pass' as const) : ('fail' as const),
    label: allPass ? '合格' : '不合格',
    tagType: allPass ? ('success' as const) : ('danger' as const),
    detail: parts.join('；'),
  }
})

// ── Formatters ──────────────────────────────────────────────────
function fmt(v: number | null, d = 1): string {
  return v !== null && Number.isFinite(v) ? v.toFixed(d) : '—'
}
</script>

<template>
  <div class="strength-eval-card">
    <!-- Header -->
    <div class="sec-header">
      <span class="sec-title">28d抗压强度试验数据</span>
      <span class="sec-hint">每组 3 条记录，共 ≥6 组</span>
      <el-button
        v-if="!readonly"
        size="small"
        type="primary"
        plain
        @click="addGroup"
      >
        <el-icon><Plus /></el-icon>
        新增分组
      </el-button>
    </div>

    <!-- Groups table -->
    <div class="groups-table-wrap">
      <table class="groups-table">
        <thead>
          <tr>
            <th style="width:80px">分组</th>
            <th>试件 1 (MPa)</th>
            <th>试件 2 (MPa)</th>
            <th>试件 3 (MPa)</th>
            <th style="width:90px">组平均值<br>(MPa)</th>
            <th style="width:70px">取舍</th>
            <th v-if="!readonly" style="width:50px"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(group, gi) in groups"
            :key="group.id"
            :class="{
              'row-trimmed': groupEvals[gi]?.trimmed && !groupEvals[gi]?.invalid,
              'row-invalid': groupEvals[gi]?.invalid,
            }"
          >
            <td class="td-center td-group">
              <span class="group-id">{{ group.id }}</span>
            </td>
            <td v-for="vi in 3" :key="vi" class="td-center" :class="{ 'td-trimmed': groupEvals[gi]?.trimmedIndices.includes(vi - 1) }">
              <el-input-number
                v-if="!readonly"
                :model-value="group.values[vi - 1]"
                @update:model-value="v => updateValue(gi, vi - 1, v)"
                :min="0"
                :max="400"
                :step="0.1"
                :precision="1"
                size="small"
                controls-position="right"
                style="width:100%"
                placeholder="—"
                :class="{ 'input-trimmed': groupEvals[gi]?.trimmedIndices.includes(vi - 1) }"
              />
              <span v-else class="readonly-val" :class="{ 'val-trimmed': groupEvals[gi]?.trimmedIndices.includes(vi - 1) }">
                {{ fmt(group.values[vi - 1]) }}
              </span>
            </td>
            <td class="td-center td-avg">
              <span v-if="groupEvals[gi]?.invalid" class="avg-invalid">无效</span>
              <span v-else-if="groupEvals[gi]?.value !== null" class="avg-val">
                {{ fmt(groupEvals[gi]!.value, 1) }}
              </span>
              <span v-else class="avg-pending">待完善</span>
            </td>
            <td class="td-center">
              <el-tag
                v-if="groupEvals[gi]?.allFilled && groupEvals[gi]?.invalid"
                type="danger"
                size="small"
              >
                无效
              </el-tag>
              <el-tag
                v-else-if="groupEvals[gi]?.allFilled && groupEvals[gi]?.trimmed"
                type="warning"
                size="small"
              >
                已取舍
              </el-tag>
              <el-tag
                v-else-if="groupEvals[gi]?.allFilled && !groupEvals[gi]?.trimmed"
                type="success"
                size="small"
              >
                正常
              </el-tag>
              <span v-else class="td-dash">—</span>
            </td>
            <td v-if="!readonly" class="td-center">
              <el-button
                size="small"
                text
                type="danger"
                :disabled="groups.length <= 6"
                @click="removeGroup(gi)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Summary statistics -->
    <div class="summary-row">
      <div class="summary-item">
        <span class="summary-label">组数</span>
        <span class="summary-val">{{ groups.length }}</span>
      </div>
      <div class="summary-item">
        <span class="summary-label">总体平均值</span>
        <span class="summary-val summary-val--primary">{{ fmt(overallAvg, 1) }} MPa</span>
      </div>
      <div class="summary-item">
        <span class="summary-label">组均值最小值</span>
        <span class="summary-val">{{ fmt(minGroupAvg, 1) }} MPa</span>
      </div>
      <div class="summary-item">
        <span class="summary-label">{{ multiplier.toFixed(2) }} × 强度等级</span>
        <span class="summary-val summary-val--primary">{{ strengthGrade !== null ? fmt(strengthGrade * multiplier, 1) : '—' }} MPa</span>
      </div>
      <div class="summary-item">
        <span class="summary-label">0.95 × 强度等级</span>
        <span class="summary-val">{{ strengthGrade !== null ? fmt(strengthGrade * 0.95, 1) : '—' }} MPa</span>
      </div>
    </div>

    <!-- Evaluation result -->
    <div v-if="allComplete" class="eval-bar" :class="evaluation.status === 'pass' ? 'eval-bar--pass' : 'eval-bar--fail'">
      <el-icon :size="18">
        <component :is="evaluation.status === 'pass' ? 'CircleCheck' : 'Warning'" />
      </el-icon>
      <span class="eval-bar__label">强度评判：</span>
      <el-tag :type="evaluation.tagType" size="default">{{ evaluation.label }}</el-tag>
      <span class="eval-bar__detail">{{ evaluation.detail }}</span>
    </div>
    <div v-else class="eval-bar eval-bar--pending">
      <el-icon :size="18"><InfoFilled /></el-icon>
      <span class="eval-bar__detail">{{ evaluation.detail }}</span>
    </div>
  </div>
</template>

<style scoped>
.strength-eval-card {
  border: 1px solid #e5e9f2;
  border-radius: 12px;
  background: #fff;
  padding: 16px;
}

.sec-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}
.sec-title {
  font-size: 15px;
  font-weight: 700;
  color: #1e3c72;
}
.sec-hint {
  font-size: 11px;
  color: #9ca3af;
  flex: 1;
}

.groups-table-wrap {
  overflow-x: auto;
  margin-bottom: 12px;
  max-height: 420px;
  overflow-y: auto;
}

.groups-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.groups-table th {
  background: #f8f9fc;
  color: #374151;
  font-weight: 600;
  padding: 8px 6px;
  border: 1px solid #e5e9f2;
  text-align: center;
  position: sticky;
  top: 0;
  z-index: 1;
}
.groups-table td {
  border: 1px solid #e5e9f2;
  padding: 6px;
}

.td-center { text-align: center; }
.td-group { background: #f8f9fc; }
.group-id {
  font-weight: 700;
  color: #1e3c72;
  font-size: 13px;
}

.td-avg { background: #fafbfd; }
.avg-val {
  font-weight: 700;
  color: #1e3c72;
}
.avg-pending {
  color: #9ca3af;
  font-size: 11px;
}
.avg-invalid {
  color: #e74c3c;
  font-weight: 700;
  font-size: 11px;
}
.td-dash { color: #ccc; }

.row-trimmed td {
  background: #fffbe6;
}
.row-trimmed .td-avg {
  background: #fff8d4;
}

/* ── Invalid row ────────────────────────────────────────────── */
.row-invalid td {
  background: #fff0f0;
}
.row-invalid .td-avg {
  background: #ffe0e0;
}

.readonly-val {
  font-weight: 500;
  color: #374151;
}

/* ── Trimmed cells ─────────────────────────────────────────── */
.td-trimmed {
  background: #fff0f0 !important;
}
.val-trimmed {
  color: #c0392b;
  text-decoration: line-through;
  font-weight: 400;
}
.input-trimmed :deep(.el-input__inner) {
  color: #c0392b;
  text-decoration: line-through;
}

/* ── Summary ──────────────────────────────────────────────────── */
.summary-row {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  padding: 10px 14px;
  background: #f8f9fc;
  border-radius: 8px;
  margin-bottom: 12px;
}
.summary-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.summary-label {
  font-size: 12px;
  color: #6b7280;
}
.summary-val {
  font-size: 13px;
  font-weight: 700;
  color: #374151;
}
.summary-val--primary {
  color: #1e3c72;
  font-size: 15px;
}

/* ── Evaluation bar ───────────────────────────────────────────── */
.eval-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
}
.eval-bar--pass {
  background: #d1e7dd;
  border: 1px solid #82c88a;
  color: #0f5132;
}
.eval-bar--fail {
  background: #f8d7da;
  border: 1px solid #e08d95;
  color: #842029;
}
.eval-bar--pending {
  background: #e7f0ff;
  border: 1px solid #a3c4f3;
  color: #1e3c72;
}
.eval-bar__label {
  font-weight: 700;
}
.eval-bar__detail {
  flex: 1;
  font-size: 12px;
}
</style>
