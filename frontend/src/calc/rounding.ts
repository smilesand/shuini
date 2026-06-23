/**
 * calc/rounding.ts
 * ================
 * 计算引擎统一舍入工具。
 *
 * 后端历史上对不同模块使用了两种舍入口径，迁移到前端后必须逐一对齐，
 * 否则会出现跨端（旧服务端结果 vs 新前端结果）数值不一致：
 *
 *   1. `pyRound`  —— 复刻 Python 内置 `round()` 的「四舍六入五取偶」（银行家舍入）。
 *      用于基础计算模块：水胶比、骨料、胶凝材料、水与外加剂、适配调整。
 *   2. `jsRound`  —— 复刻后端 hpc_trial / uhpc 服务里使用的 `floor(x * f + 0.5) / f`。
 *      该口径与 JavaScript `Math.round`（正数）一致，用于试配相关计算。
 *   3. `truncDigits` —— 直接朝零截断到指定小数位，复刻推荐水胶比展示用的 `math.trunc`。
 *
 * 之所以保留两套舍入，是为了与既有服务端逐字段一致；在真实输入下二者仅在
 * 恰好命中 0.5 边界时才有差异，但为保证迁移「零口径漂移」仍严格区分。
 */

/**
 * 银行家舍入（四舍六入五取偶），对齐 Python `round(value, digits)`。
 *
 * @param value  原始数值
 * @param digits 保留小数位，默认 0
 */
export function pyRound(value: number, digits = 0): number {
  if (!Number.isFinite(value)) return value
  const factor = 10 ** digits
  const x = value * factor
  const floor = Math.floor(x)
  const diff = x - floor
  let rounded: number
  // 命中 0.5 边界时取偶；用极小 epsilon 容忍浮点误差。
  if (Math.abs(diff - 0.5) < 1e-9) {
    rounded = floor % 2 === 0 ? floor : floor + 1
  } else {
    rounded = Math.round(x)
  }
  return rounded / factor
}

/**
 * `floor(value * f + 0.5) / f` 风格舍入，对齐后端 hpc_trial / uhpc 的 `_round_js`。
 *
 * @param value  原始数值
 * @param digits 保留小数位，默认 4
 */
export function jsRound(value: number, digits = 4): number {
  if (!Number.isFinite(value)) return value
  const factor = 10 ** digits
  return Math.floor(value * factor + 0.5) / factor
}

/**
 * 朝零截断到指定小数位，对齐后端的 `math.trunc` / `int()` 截断。
 *
 * @param value  原始数值
 * @param digits 保留小数位，默认 2
 */
export function truncDigits(value: number, digits = 2): number {
  if (!Number.isFinite(value)) return value
  const factor = 10 ** digits
  return Math.trunc(value * factor) / factor
}
