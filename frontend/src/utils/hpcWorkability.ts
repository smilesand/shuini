export type HpcWorkabilityMetric = 'slump' | 'spread'

export type HpcWorkabilityReferenceCode = 'SF0' | 'SF1' | 'SF2' | 'SF3'

export interface HpcWorkabilityReferenceOption {
  code: HpcWorkabilityReferenceCode
  desc: string
  range: string
  metric: HpcWorkabilityMetric
  min: number
  max: number
}

export interface HpcWorkabilityEvaluation {
  status: 'pending' | 'pass' | 'fail'
  label: string
  tagType: 'info' | 'success' | 'danger'
  detail: string
  reference: HpcWorkabilityReferenceOption | null
}

export const HPC_WORKABILITY_REFERENCES: HpcWorkabilityReferenceOption[] = [
  { code: 'SF0', desc: '坍落度 180~220mm', range: '0.37 ~ 0.40', metric: 'slump', min: 180, max: 220 },
  { code: 'SF1', desc: '扩展度 500~600mm', range: '0.35 ~ 0.38', metric: 'spread', min: 500, max: 600 },
  { code: 'SF2', desc: '扩展度 600~700mm', range: '0.32 ~ 0.36', metric: 'spread', min: 600, max: 700 },
  { code: 'SF3', desc: '扩展度 700~800mm', range: '0.30 ~ 0.32', metric: 'spread', min: 700, max: 800 },
]

function formatMeasure(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

export function getHpcWorkabilityReference(code: string | null | undefined) {
  if (!code) {
    return null
  }

  return HPC_WORKABILITY_REFERENCES.find((item) => item.code === code) ?? null
}

/**
 * 根据用户输入的设计要求（坍落度 / 扩展度）匹配工作性能参考等级。
 * - 坍落度落在 SF0 范围内 → SF0
 * - 扩展度落在 SF1/SF2/SF3 范围内 → 对应等级
 * 返回所有命中的等级（用于表格高亮）。
 */
export function matchHpcWorkabilityReferences(
  slump: number | null | undefined,
  spread: number | null | undefined,
): HpcWorkabilityReferenceCode[] {
  const matched: HpcWorkabilityReferenceCode[] = []
  for (const ref of HPC_WORKABILITY_REFERENCES) {
    const measured = ref.metric === 'slump' ? slump : spread
    if (measured === null || measured === undefined || !Number.isFinite(measured)) {
      continue
    }
    if (measured >= ref.min && measured <= ref.max) {
      matched.push(ref.code)
    }
  }
  return matched
}

/** 返回第一个命中的工作性能等级（用于自动确定 Vg 参考范围）。 */
export function resolveHpcWorkabilityCode(
  slump: number | null | undefined,
  spread: number | null | undefined,
): HpcWorkabilityReferenceCode | null {
  return matchHpcWorkabilityReferences(slump, spread)[0] ?? null
}

export function evaluateHpcWorkability(
  code: HpcWorkabilityReferenceCode | null | undefined,
  slump: number | null | undefined,
  spread: number | null | undefined,
): HpcWorkabilityEvaluation {
  const reference = getHpcWorkabilityReference(code)

  if (!reference) {
    return {
      status: 'pending',
      label: '待评价',
      tagType: 'info',
      detail: '请先在“骨料用量”中选择 Vg 参考范围。',
      reference: null,
    }
  }

  const metricLabel = reference.metric === 'slump' ? '坍落度' : '扩展度'
  const measured = reference.metric === 'slump' ? slump : spread

  if (measured === null || measured === undefined || !Number.isFinite(measured)) {
    return {
      status: 'pending',
      label: '待输入',
      tagType: 'info',
      detail: `当前参考范围为 ${reference.desc}，请输入${metricLabel}。`,
      reference,
    }
  }

  const passed = measured >= reference.min && measured <= reference.max

  return {
    status: passed ? 'pass' : 'fail',
    label: passed ? '合格' : '不合格',
    tagType: passed ? 'success' : 'danger',
    detail: `${reference.desc}，当前${metricLabel} ${formatMeasure(measured)} mm。`,
    reference,
  }
}