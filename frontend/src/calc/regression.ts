/**
 * calc/regression.ts
 * ==================
 * 回归系数拟合引擎，由后端 services/regression.py 迁移而来。
 *
 * 后端使用 numpy.linalg.lstsq 做最小二乘；浏览器无 numpy，这里用「正规方程 +
 * 高斯消元（部分主元）」实现等价的满秩最小二乘解。对于本场景的小型良态系统，
 * 该实现与 lstsq 结果在数值上一致。
 *
 * 策略：依次尝试三个候选模型，按 R² 提升阈值（0.001）自动升级，最终把模型系数
 * 换算为鲍罗米公式标准回归系数 αa、αb、αc。
 *
 *   模型1 : z = a·xy + b·y           （最简单）
 *   模型2 : z = a·xy + b·y + c        （带截距）
 *   模型3 : z = a·xy + b·y + c·y² + d （二次项，最复杂）
 *
 * α 系数换算（模型1/2）：αa = a；αb = -b/a；αc = -c（模型1 时 αc = 0）。
 * 模型3 因含 y² 项无法直接换算，退化为模型2 重新拟合后提取。
 */
import { pyRound } from './rounding'

export interface RegressionResult {
  aa: number
  ab: number
  ac: number
  r2: number
}

interface ModelFit {
  name: 'model1' | 'model2' | 'model3'
  label: string
  coeffs: number[]
  r2: number
}

/**
 * 解正规方程 (XᵀX) c = Xᵀz，返回最小二乘系数。
 * 使用部分主元高斯消元，等价于满秩超定系统的 lstsq 解。
 */
function solveLeastSquares(columns: number[][], z: number[]): number[] {
  const k = columns.length // 变量个数
  const n = z.length // 样本数

  // 构造正规方程的增广矩阵 A = XᵀX (k×k)，b = Xᵀz (k)
  const A: number[][] = Array.from({ length: k }, () => new Array(k).fill(0))
  const b: number[] = new Array(k).fill(0)
  for (let i = 0; i < k; i++) {
    for (let j = 0; j < k; j++) {
      let sum = 0
      for (let r = 0; r < n; r++) sum += columns[i][r] * columns[j][r]
      A[i][j] = sum
    }
    let sum = 0
    for (let r = 0; r < n; r++) sum += columns[i][r] * z[r]
    b[i] = sum
  }

  // 高斯消元（部分主元）
  for (let col = 0; col < k; col++) {
    let pivot = col
    for (let row = col + 1; row < k; row++) {
      if (Math.abs(A[row][col]) > Math.abs(A[pivot][col])) pivot = row
    }
    if (pivot !== col) {
      ;[A[col], A[pivot]] = [A[pivot], A[col]]
      ;[b[col], b[pivot]] = [b[pivot], b[col]]
    }
    const diag = A[col][col]
    if (Math.abs(diag) < 1e-12) continue // 奇异，跳过（与 lstsq 的最小范数解近似）
    for (let row = col + 1; row < k; row++) {
      const factor = A[row][col] / diag
      if (factor === 0) continue
      for (let c = col; c < k; c++) A[row][c] -= factor * A[col][c]
      b[row] -= factor * b[col]
    }
  }

  // 回代
  const coeffs = new Array(k).fill(0)
  for (let row = k - 1; row >= 0; row--) {
    let sum = b[row]
    for (let c = row + 1; c < k; c++) sum -= A[row][c] * coeffs[c]
    const diag = A[row][row]
    coeffs[row] = Math.abs(diag) < 1e-12 ? 0 : sum / diag
  }
  return coeffs
}

/** 计算决定系数 R²，与后端 _lstsq_fit 保持一致（保留 6 位）。 */
function computeR2(columns: number[][], z: number[], coeffs: number[]): number {
  const n = z.length
  const mean = z.reduce((s, v) => s + v, 0) / n
  let ssRes = 0
  let ssTot = 0
  for (let r = 0; r < n; r++) {
    let pred = 0
    for (let i = 0; i < columns.length; i++) pred += columns[i][r] * coeffs[i]
    ssRes += (z[r] - pred) ** 2
    ssTot += (z[r] - mean) ** 2
  }
  const r2 = ssTot > 0 ? 1.0 - ssRes / ssTot : 0.0
  return pyRound(r2, 6)
}

/** 解析 CSV 文本，返回 {x, y, z}，自动跳过表头/非数字行。 */
function parseCsv(csvText: string): { x: number[]; y: number[]; z: number[] } {
  const x: number[] = []
  const y: number[] = []
  const z: number[] = []
  const lines = csvText.trim().split(/\r?\n/)
  for (const line of lines) {
    const cells = line.split(',')
    if (cells.length < 3) continue
    const a = Number.parseFloat(cells[0].trim())
    const b = Number.parseFloat(cells[1].trim())
    const c = Number.parseFloat(cells[2].trim())
    if (Number.isNaN(a) || Number.isNaN(b) || Number.isNaN(c)) continue
    x.push(a)
    y.push(b)
    z.push(c)
  }
  if (x.length < 3) {
    throw new Error(`有效数据行不足（当前 ${x.length} 行），至少需要 3 行`)
  }
  return { x, y, z }
}

/** 拟合三个候选模型。 */
function fitAllModels(x: number[], y: number[], z: number[]): ModelFit[] {
  const xy = x.map((xi, i) => xi * y[i])
  const ones = x.map(() => 1)
  const ySq = y.map((yi) => yi * yi)

  const cols1 = [xy, y]
  const c1 = solveLeastSquares(cols1, z)

  const cols2 = [xy, y, ones]
  const c2 = solveLeastSquares(cols2, z)

  const cols3 = [xy, y, ySq, ones]
  const c3 = solveLeastSquares(cols3, z)

  return [
    { name: 'model1', label: 'z=a·xy+b·y', coeffs: c1, r2: computeR2(cols1, z, c1) },
    { name: 'model2', label: 'z=a·xy+b·y+c', coeffs: c2, r2: computeR2(cols2, z, c2) },
    { name: 'model3', label: 'z=a·xy+b·y+c·y²+d', coeffs: c3, r2: computeR2(cols3, z, c3) },
  ]
}

/** 从最简单模型开始，R² 提升超过阈值则升级，否则停止。 */
function selectBestModel(models: ModelFit[], threshold = 0.001): ModelFit {
  let best = models[0]
  for (const m of models.slice(1)) {
    if (m.r2 - best.r2 > threshold) best = m
    else break
  }
  return best
}

/** 把模型系数换算为 αa, αb, αc。模型3 退化为模型2 重拟合。 */
function extractAlpha(
  model: ModelFit,
  x: number[],
  y: number[],
  z: number[],
): [number, number, number] {
  if (model.name === 'model1') {
    const [a, b] = model.coeffs
    return [a, -b / a, 0.0]
  }
  if (model.name === 'model2') {
    const [a, b, c] = model.coeffs
    return [a, -b / a, -c]
  }
  // model3 → 退化为 model2 重新拟合
  const xy = x.map((xi, i) => xi * y[i])
  const ones = x.map(() => 1)
  const c2 = solveLeastSquares([xy, y, ones], z)
  const [a, b, c] = c2
  return [a, -b / a, -c]
}

/** 从 CSV 文本拟合鲍罗米公式回归系数，输出与后端 fit_regression_coefficients 一致。 */
export function fitRegressionCoefficients(csvText: string): RegressionResult {
  const { x, y, z } = parseCsv(csvText)
  const models = fitAllModels(x, y, z)
  const best = selectBestModel(models)
  const [aa, ab, ac] = extractAlpha(best, x, y, z)
  return {
    aa: pyRound(aa, 6),
    ab: pyRound(ab, 6),
    ac: pyRound(ac, 6),
    r2: pyRound(best.r2, 6),
  }
}
