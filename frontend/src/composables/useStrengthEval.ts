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
  /** The original 3 values for display */
  originalValues: (number | null)[]
}

let nextId = 1
function newGroupId(): string {
  return `G${String(nextId++).padStart(2, '0')}`
}

// ── Pure calculation helpers ─────────────────────────────────────

/**
 * Compute group representative value:
 * 1. Calculate mean of all 3 values
 * 2. If max > mean * 1.15 or min < mean * 0.85, remove both max & min, use median
 * 3. Otherwise use the mean
 */
export function computeGroupValue(values: (number | null)[]): {
  value: number | null
  trimmed: boolean
  /** 0-based indices of the trimmed values in the original array */
  trimmedIndices: number[]
} {
  const nums = values.filter((v): v is number => v !== null && Number.isFinite(v))
  if (nums.length < 3) {
    // Need all 3 values to compute
    return { value: null, trimmed: false, trimmedIndices: [] }
  }

  // Locate original positions of min / max
  let minIdx = -1
  let maxIdx = -1
  for (let i = 0; i < values.length; i++) {
    const v = values[i]
    if (v === null || !Number.isFinite(v)) continue
    if (minIdx === -1 || v < (values[minIdx] as number)) minIdx = i
    if (maxIdx === -1 || v > (values[maxIdx] as number)) maxIdx = i
  }

  const sorted = [...nums].sort((a, b) => a - b)
  const min = sorted[0]
  const max = sorted[2]
  const mean = (sorted[0] + sorted[1] + sorted[2]) / 3

  if (mean === 0) return { value: 0, trimmed: false, trimmedIndices: [] }

  const maxDev = Math.abs((max - mean) / mean)
  const minDev = Math.abs((min - mean) / mean)

  if (maxDev > 0.15 || minDev > 0.15) {
    // Trim both extremes, use median
    return { value: sorted[1], trimmed: true, trimmedIndices: [minIdx, maxIdx] }
  }

  return { value: mean, trimmed: false, trimmedIndices: [] }
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
      const { value, trimmed } = computeGroupValue(g.values)
      return {
        groupAvg: value,
        trimmed,
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

  // ── Computed: evaluation against targets ────────────────────
  function evaluate(
    targetStrength: number | null,   // 配制强度
    strengthGrade: number | null,    // 强度等级 (e.g., C80 → 80)
  ) {
    const ov = overallAvg.value
    const minG = minGroupAvg.value
    const complete = allGroupsComplete.value

    if (!complete || ov === null || targetStrength === null) {
      return {
        status: 'pending' as const,
        label: '待评价',
        tagType: 'info' as const,
        detail: '请完成所有 6 组（每组 3 条）强度数据填写。',
        overallPass: null as boolean | null,
        minGroupPass: null as boolean | null,
      }
    }

    const overallPass = ov >= targetStrength
    const minThreshold = strengthGrade !== null ? strengthGrade * 0.95 : null
    const minGroupPass = minThreshold !== null ? (minG !== null && minG >= minThreshold) : null

    const allPass = overallPass && (minGroupPass !== false)

    let detail = `总体平均值 ${ov.toFixed(1)} MPa`
    if (overallPass) {
      detail += ` ≥ 配制强度 ${targetStrength.toFixed(1)} MPa`
    } else {
      detail += ` < 配制强度 ${targetStrength.toFixed(1)} MPa，差值 ${(targetStrength - ov).toFixed(1)} MPa`
    }

    if (minThreshold !== null && minG !== null) {
      detail += `；组均值最小值 ${minG.toFixed(1)} MPa`
      if (minGroupPass) {
        detail += ` ≥ 0.95×强度等级(${minThreshold.toFixed(1)} MPa)`
      } else {
        detail += ` < 0.95×强度等级(${minThreshold.toFixed(1)} MPa)`
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
