import { computed, ref } from 'vue'

// ── Types ────────────────────────────────────────────────────────
export interface StrengthGroup {
  id: string
  values: (number | null)[]  // exactly 3 entries per group
}

export interface StrengthEvalResult {
  /** Group representative value after outlier trimming */
  groupAvg: number | null
  /** Whether the group had an outlier trimmed */
  trimmed: boolean
  /** Whether the group result is invalid (both extremes deviate >15% from median) */
  invalid: boolean
  /** The original 3 values for display */
  originalValues: (number | null)[]
}

let nextId = 1
function newGroupId(): string {
  return `G${String(nextId++).padStart(2, '0')}`
}

// ── Pure calculation helpers ─────────────────────────────────────

/**
 * Compute group representative value per JGJ/T 标准:
 * 1. 取3个试件测值的算术平均值作为该组试件的强度值，精确至0.1MPa
 * 2. 当最大值或最小值中有一个与中间值的差值超过中间值的15%时，
 *    剔除最大及最小值，取中间值作为该组试件的抗压强度值
 * 3. 当最大值和最小值与中间值的差值均超过中间值的15%时，
 *    该组试件的试验结果无效
 */
export function computeGroupValue(values: (number | null)[]): {
  value: number | null
  trimmed: boolean
  /** Whether the group result is invalid (both extremes deviate >15% from median) */
  invalid: boolean
  /** 0-based indices of the trimmed values in the original array */
  trimmedIndices: number[]
} {
  const nums = values.filter((v): v is number => v !== null && Number.isFinite(v))
  if (nums.length < 3) {
    return { value: null, trimmed: false, invalid: false, trimmedIndices: [] }
  }

  // Locate original positions of min / max
  let minIdx = -1
  let maxIdx = -1
  let midIdx = -1
  for (let i = 0; i < values.length; i++) {
    const v = values[i]
    if (v === null || !Number.isFinite(v)) continue
    if (minIdx === -1 || v < (values[minIdx] as number)) minIdx = i
    if (maxIdx === -1 || v > (values[maxIdx] as number)) maxIdx = i
  }
  // Find mid index (the one that is neither min nor max)
  for (let i = 0; i < values.length; i++) {
    const v = values[i]
    if (v === null || !Number.isFinite(v)) continue
    if (i !== minIdx && i !== maxIdx) { midIdx = i; break }
  }

  const sorted = [...nums].sort((a, b) => a - b)
  const min = sorted[0]
  const mid = sorted[1]
  const max = sorted[2]
  const mean = (min + mid + max) / 3

  if (mid === 0) return { value: 0, trimmed: false, invalid: false, trimmedIndices: [] }

  const maxDev = Math.abs((max - mid) / mid)
  const minDev = Math.abs((min - mid) / mid)

  // Rule 3: both extremes deviate >15% from median → invalid
  if (maxDev > 0.15 && minDev > 0.15) {
    return { value: null, trimmed: false, invalid: true, trimmedIndices: [] }
  }

  // Rule 2: one extreme deviates >15% from median → trim both, use median
  if (maxDev > 0.15 || minDev > 0.15) {
    const midRounded = Math.round(mid * 10) / 10 // 精确至0.1MPa
    return { value: midRounded, trimmed: true, invalid: false, trimmedIndices: [minIdx, maxIdx] }
  }

  // Rule 1: use arithmetic mean, rounded to 0.1MPa
  const meanRounded = Math.round(mean * 10) / 10
  return { value: meanRounded, trimmed: false, invalid: false, trimmedIndices: [] }
}

// ── Composable ───────────────────────────────────────────────────

export function useStrengthEval(
  initialGroups?: StrengthGroup[],
) {
  // State
  const groups = ref<StrengthGroup[]>(
    initialGroups && initialGroups.length > 0
      ? initialGroups
      : defaultGroups(),
  )

  // ── Group CRUD ──────────────────────────────────────────────
  function addGroup() {
    groups.value.push({
      id: newGroupId(),
      values: [null, null, null],
    })
  }

  function removeGroup(groupId: string) {
    if (groups.value.length <= 6) {
      return // minimum 6 groups
    }
    groups.value = groups.value.filter(g => g.id !== groupId)
  }

  function resetToDefault() {
    groups.value = defaultGroups()
  }

  // ── Computed: per-group evaluation ──────────────────────────
  const groupResults = computed<StrengthEvalResult[]>(() =>
    groups.value.map(g => {
      const { value, trimmed, invalid } = computeGroupValue(g.values)
      return {
        groupAvg: value,
        trimmed,
        invalid,
        originalValues: [...g.values],
      }
    }),
  )

  // ── Computed: overall statistics ────────────────────────────
  const overallAvg = computed<number | null>(() => {
    const avgs = groupResults.value
      .map(r => r.groupAvg)
      .filter((v): v is number => v !== null)
    if (avgs.length === 0) return null
    return avgs.reduce((s, v) => s + v, 0) / avgs.length
  })

  const minGroupAvg = computed<number | null>(() => {
    const avgs = groupResults.value
      .map(r => r.groupAvg)
      .filter((v): v is number => v !== null)
    if (avgs.length === 0) return null
    return Math.min(...avgs)
  })

  const allGroupsComplete = computed(() =>
    groupResults.value.every(r => r.groupAvg !== null),
  )

  const hasInvalidGroup = computed(() =>
    groupResults.value.some(r => r.invalid),
  )

  // ── Computed: evaluation against targets ────────────────────
  function evaluate(
    _targetStrength: number | null,   // 配制强度 (保留参数兼容性，实际使用 multiplier × 强度等级)
    strengthGrade: number | null,    // 强度等级 (e.g., C80 → 80)
    strengthMultiplier: number = 1.15,  // HPC=1.15, UHPC=1.10
  ) {
    const ov = overallAvg.value
    const minG = minGroupAvg.value
    const complete = allGroupsComplete.value
    const hasInvalid = hasInvalidGroup.value

    if (!complete || ov === null) {
      const reason = hasInvalid
        ? '存在无效试验组（最大值和最小值与中间值的差值均超过中间值的15%），请修正数据。'
        : '请完成所有 6 组（每组 3 条）强度数据填写。'
      return {
        status: 'pending' as const,
        label: '待评价',
        tagType: 'info' as const,
        detail: reason,
        overallPass: null as boolean | null,
        minGroupPass: null as boolean | null,
      }
    }

    // 六组试块强度平均值 ≥ multiplier × 强度等级
    const avgThreshold = strengthGrade !== null ? strengthGrade * strengthMultiplier : null
    const overallPass = avgThreshold !== null ? ov >= avgThreshold : null

    // 最小值 ≥ 0.95 × 强度等级
    const minThreshold = strengthGrade !== null ? strengthGrade * 0.95 : null
    const minGroupPass = minThreshold !== null && minG !== null ? minG >= minThreshold : null

    const allPass = overallPass !== false && (minGroupPass !== false)

    const multLabel = strengthMultiplier.toFixed(2)

    let detail = `总体平均值 ${ov.toFixed(1)} MPa`
    if (avgThreshold !== null) {
      if (overallPass) {
        detail += ` ≥ ${multLabel}×强度等级(${avgThreshold.toFixed(1)} MPa)`
      } else {
        detail += ` < ${multLabel}×强度等级(${avgThreshold.toFixed(1)} MPa)，差值 ${(avgThreshold - ov).toFixed(1)} MPa`
      }
    }

    if (minThreshold !== null && minG !== null) {
      detail += `；组均值最小值 ${minG.toFixed(1)} MPa`
      if (minGroupPass) {
        detail += ` ≥ 0.95×强度等级(${minThreshold.toFixed(1)} MPa)`
      } else {
        detail += ` < 0.95×强度等级(${minThreshold.toFixed(1)} MPa)，差值 ${(minThreshold - minG).toFixed(1)} MPa`
      }
    }

    return {
      status: allPass ? ('pass' as const) : ('fail' as const),
      label: allPass ? '合格' : '不合格',
      tagType: allPass ? ('success' as const) : ('danger' as const),
      detail,
      overallPass,
      minGroupPass,
    }
  }

  // ── Serialization ───────────────────────────────────────────
  function toSnapshot(): StrengthGroup[] {
    return groups.value.map(g => ({
      id: g.id,
      values: [...g.values],
    }))
  }

  function fromSnapshot(data: unknown) {
    if (!Array.isArray(data)) return
    const loaded = data as StrengthGroup[]
    if (loaded.length > 0) {
      // Reset id counter based on loaded data to avoid collisions
      const maxNum = loaded.reduce((max, g) => {
        const num = parseInt(g.id.replace('G', ''), 10)
        return Number.isFinite(num) ? Math.max(max, num) : max
      }, 0)
      nextId = maxNum + 1
      groups.value = loaded.map(g => ({
        id: g.id,
        values: Array.isArray(g.values) ? g.values.slice(0, 3) : [null, null, null],
      }))
    }
  }

  return {
    groups,
    groupResults,
    overallAvg,
    minGroupAvg,
    allGroupsComplete,
    addGroup,
    removeGroup,
    resetToDefault,
    evaluate,
    toSnapshot,
    fromSnapshot,
  }
}

function defaultGroups(): StrengthGroup[] {
  return Array.from({ length: 6 }, () => ({
    id: newGroupId(),
    values: [null, null, null] as (number | null)[],
  }))
}
