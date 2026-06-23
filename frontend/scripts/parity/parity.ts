/**
 * parity/parity.ts
 * ================
 * 前端计算引擎（src/calc）与后端服务（backend/services）的一致性校验。
 *
 * 流程：
 *   1. 读取共享夹具 fixtures.json 与由 gen_golden.py 生成的 golden.json。
 *   2. 用前端引擎对每个夹具求值。
 *   3. 与服务端期望输出逐字段深度比对（数值带容差，字符串/布尔精确比对）。
 *
 * 运行：
 *   python frontend/scripts/parity/gen_golden.py   # 先生成 golden.json
 *   npx tsx frontend/scripts/parity/parity.ts      # 再比对
 *
 * 任意字段不一致时进程以非零状态退出，便于在 CI 中作为门禁。
 */
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

import {
  calcWaterBinder,
  calcAggregate,
  calcBinder,
  calcWaterAdmixture,
  fitRegressionCoefficients,
  calcAdapt,
  calcHpcTrial,
  calcUhpcMix,
  calcUhpcTrial,
} from '../../src/calc/index'
import type {
  WaterBinderInput,
  AggregateInput,
  BinderInput,
  WaterAdmixtureInput,
  AdaptInput,
} from '../../src/calc/index'
import type { HpcTrialReq, UhpcMixReq, UhpcTrialReq } from '../../src/api/calc'

const HERE = dirname(fileURLToPath(import.meta.url))

type Json = string | number | boolean | null | Json[] | { [k: string]: Json }
interface Case {
  name: string
  input?: Record<string, Json>
  csv_text?: string
}
interface GoldenCase {
  name: string
  expected: Json
}

const fixtures = JSON.parse(readFileSync(join(HERE, 'fixtures.json'), 'utf-8')) as Record<string, Case[]>
const golden = JSON.parse(readFileSync(join(HERE, 'golden.json'), 'utf-8')) as Record<string, GoldenCase[]>

const TOLERANCE = 1e-9

let failures = 0
let comparisons = 0

/** 深度比对，记录第一处差异路径。返回 null 表示一致。 */
function diff(actual: unknown, expected: unknown, path: string): string | null {
  comparisons += 1
  if (expected === null || expected === undefined) {
    return actual === null || actual === undefined ? null : `${path}: 期望 null，实际 ${String(actual)}`
  }
  if (typeof expected === 'number') {
    if (typeof actual !== 'number' || Number.isNaN(actual)) {
      return `${path}: 期望数字 ${expected}，实际 ${String(actual)}`
    }
    return Math.abs(actual - expected) <= TOLERANCE
      ? null
      : `${path}: 期望 ${expected}，实际 ${actual}（差 ${Math.abs(actual - expected)}）`
  }
  if (typeof expected === 'string' || typeof expected === 'boolean') {
    return actual === expected ? null : `${path}: 期望 ${JSON.stringify(expected)}，实际 ${JSON.stringify(actual)}`
  }
  if (Array.isArray(expected)) {
    if (!Array.isArray(actual)) return `${path}: 期望数组，实际 ${typeof actual}`
    if (actual.length !== expected.length) {
      return `${path}: 数组长度 期望 ${expected.length}，实际 ${actual.length}`
    }
    for (let i = 0; i < expected.length; i += 1) {
      const d = diff(actual[i], expected[i], `${path}[${i}]`)
      if (d) return d
    }
    return null
  }
  // object
  if (typeof actual !== 'object' || actual === null || Array.isArray(actual)) {
    return `${path}: 期望对象，实际 ${String(actual)}`
  }
  const expObj = expected as Record<string, unknown>
  const actObj = actual as Record<string, unknown>
  for (const key of Object.keys(expObj)) {
    if (!(key in actObj)) return `${path}.${key}: 实际对象缺少该字段`
    const d = diff(actObj[key], expObj[key], `${path}.${key}`)
    if (d) return d
  }
  return null
}

function check(section: string, run: (input: Case) => unknown): void {
  const cases = fixtures[section] ?? []
  const expectedCases = golden[section] ?? []
  for (const c of cases) {
    const exp = expectedCases.find((g) => g.name === c.name)
    if (!exp) {
      failures += 1
      console.error(`  ✗ ${section}/${c.name}: golden.json 中缺少该用例（请重跑 gen_golden.py）`)
      continue
    }
    let actual: unknown
    try {
      actual = run(c)
    } catch (err) {
      failures += 1
      console.error(`  ✗ ${section}/${c.name}: 引擎抛出异常 ${(err as Error).message}`)
      continue
    }
    const d = diff(actual, exp.expected, `${section}/${c.name}`)
    if (d) {
      failures += 1
      console.error(`  ✗ ${section}/${c.name}: ${d}`)
    } else {
      console.log(`  ✓ ${section}/${c.name}`)
    }
  }
}

console.log('前端引擎 vs 服务端 计算一致性校验')
console.log('===================================')

check('water_binder', (c) => calcWaterBinder(c.input as unknown as WaterBinderInput))
check('aggregate', (c) => calcAggregate(c.input as unknown as AggregateInput))
check('binder', (c) => calcBinder(c.input as unknown as BinderInput))
check('water_admixture', (c) => calcWaterAdmixture(c.input as unknown as WaterAdmixtureInput))
check('regression', (c) => fitRegressionCoefficients((c.input?.csv_text ?? c.csv_text) as string))
check('adapt', (c) => calcAdapt(c.input as unknown as AdaptInput))
check('hpc_trial', (c) => calcHpcTrial(c.input as unknown as HpcTrialReq))
check('uhpc_mix', (c) => calcUhpcMix(c.input as unknown as UhpcMixReq))
check('uhpc_trial', (c) => calcUhpcTrial(c.input as unknown as UhpcTrialReq))

console.log('===================================')
console.log(`字段比对次数：${comparisons}`)
if (failures === 0) {
  console.log('✓ 全部用例与服务端计算一致')
  process.exit(0)
} else {
  console.error(`✗ 存在 ${failures} 处不一致`)
  process.exit(1)
}
