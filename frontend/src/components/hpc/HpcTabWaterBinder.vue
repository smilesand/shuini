<script setup lang="ts">
import { computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'
import { useCalcStore } from '../../stores/calcStore.ts'
import { uploadFitFile } from '../../api/calc.ts'
import { debounce } from '../../utils/debounce.ts'
import Formula from '../Formula.vue'
import '../../style/calc-tabs.css'

const emit = defineEmits<{ (e: 'next-step'): void }>()
const store = useCalcStore()

// 防抖 + 节流：500ms 内多次变化只计算最后一次
const debouncedCalc = debounce(() => store.calcWaterBinder(), 500)

const computedFb = computed(() => {
  const fce = store.fceG * store.gammaC
  return store.gammaF * store.gammaS * store.gammaB * store.gammaSF * fce
})

// γc 取值范围提示随水泥强度等级动态变化
const gammaCHint = computed(() =>
  store.fceG === 42.5 ? '42.5 水泥：1.05 ~ 1.16' : '52.5 水泥：1.05 ~ 1.10'
)

// ── Mass fraction ↔ coefficient recommendation ──────────────────
// Reference tables (掺量% → 系数范围 [low, high])
const COEFF_TABLE: Record<string, [number, [number, number]][]> = {
  gammaF: [[0, [1.00, 1.00]], [10, [0.90, 1.00]], [20, [0.80, 0.90]], [30, [0.70, 0.80]], [40, [0.60, 0.70]]],
  gammaS: [[0, [1.00, 1.00]], [10, [1.00, 1.00]], [20, [0.95, 1.00]], [30, [0.90, 1.00]], [40, [0.80, 0.90]]],
  gammaB: [[0, [1.00, 1.00]], [10, [0.95, 1.05]], [20, [0.90, 1.00]], [30, [0.85, 0.95]], [40, [0.80, 0.90]]],
  gammaSF: [[0, [1.00, 1.00]], [5, [1.05, 1.15]], [10, [1.10, 1.25]]],
}

/** Recommend coefficient midpoint for a given mass fraction % */
function recommendCoeff(pct: number | null, tableKey: string): number | null {
  if (pct === null || pct < 0) return null
  const table = COEFF_TABLE[tableKey]
  if (!table) return null
  // Find the bracket: last entry where pct >= bracket threshold
  let best = table[0]
  for (const entry of table) {
    if (pct >= entry[0]) best = entry
  }
  const [lo, hi] = best[1]
  return parseFloat(((lo + hi) / 2).toFixed(2))
}

// Watch mass fractions → auto-recommend coefficients
watch(
  () => [store.b1p, store.b2p, store.b3p, store.b4p] as const,
  ([b1, b2, b3, b4]) => {
    const recF = recommendCoeff(b1, 'gammaF')
    if (recF !== null) store.gammaF = recF
    const recS = recommendCoeff(b2, 'gammaS')
    if (recS !== null) store.gammaS = recS
    const recB = recommendCoeff(b3, 'gammaB')
    if (recB !== null) store.gammaB = recB
    const recSF = recommendCoeff(b4, 'gammaSF')
    if (recSF !== null) store.gammaSF = recSF
  },
)

// Cement mass fraction = 100% - sum of other four (in %)
const cementPct = computed(() => {
  const sum = (store.b1p ?? 0) + (store.b2p ?? 0) + (store.b3p ?? 0) + (store.b4p ?? 0)
  const result = 100 - sum
  return result >= 0 ? result : 0
})

// Sync cement mass fraction to store.bc (as decimal)
watch(cementPct, (val) => {
  store.bc = val / 100
}, { immediate: true })

const n = (v: number | null) => (v ?? undefined) as number | undefined

watch(
  () => [store.fbCalcMode, computedFb.value] as const,
  ([mode, val]) => {
    if (mode === 'calc') {
      store.fb = parseFloat(val.toFixed(2))
    }
  },
  { immediate: true }
)

// fb / 回归系数 变更时重新计算 W/B（fcu0 已在 store 中由 fcuk 自动计算）
watch(
  () => [store.fb, store.aa, store.ab, store.ac] as const,
  () => { if (store.fcuk && store.fb) debouncedCalc() },
)

async function onFileChange(file: UploadFile) {
  if (!file.raw) return
  try {
    store.loading = true
    const res = await uploadFitFile(file.raw)
    store.aa = res.aa
    store.ab = res.ab
    store.ac = res.ac
    ElMessage.success(`拟合完成 R²=${res.r2?.toFixed(4)}`)
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '上传解析失败')
  } finally {
    store.loading = false
  }
}
</script>

<template>
  <div>
    <!-- Section 1: 强度参数 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><DataAnalysis /></el-icon>
        强度参数输入
      </div>
      <div class="cs-section-body">
        <el-form label-position="top">
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item>
                <template #label>强度等级 f<sub>cu,k</sub></template>
                <el-input-number
                  :model-value="store.fcuk ?? undefined"
                  @update:model-value="(v: number | undefined) => store.fcuk = v ?? null"
                  :min="20" :step="5" :precision="0"
                  placeholder="如 80"
                  style="width:100%"
                >
                  <template #suffix><span class="unit-suffix">MPa</span></template>
                </el-input-number>
                <div class="input-hint">参考值 80 MPa</div>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item>
                <template #label>配制强度 f<sub>cu,0</sub></template>
                <el-input
                  :value="store.fcu0 ? store.fcu0.toFixed(2) : ''"
                  readonly placeholder="—"
                  class="computed-input"
                >
                  <template #suffix><span class="unit-suffix">MPa</span></template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item>
                <template #label>
                  胶凝材料 28d 强度 f<sub>b</sub>
                  <el-button link type="primary" size="small" style="margin-left: 8px" @click="store.fbCalcMode = store.fbCalcMode === 'input' ? 'calc' : 'input'">
                    {{ store.fbCalcMode === 'input' ? '无实测值推算' : '手工输入实测值' }}
                  </el-button>
                </template>
                <el-input-number
                  v-if="store.fbCalcMode === 'input'"
                  :model-value="store.fb ?? undefined"
                  @update:model-value="(v: number | undefined) => store.fb = v ?? null"
                  :min="1" :step="1" placeholder="如 48"
                  style="width:100%"
                >
                  <template #suffix><span class="unit-suffix">MPa</span></template>
                </el-input-number>
                <div v-if="store.fbCalcMode === 'input'" class="input-hint">参考值 48 MPa</div>
                <el-input
                  v-else
                  :value="computedFb ? computedFb.toFixed(2) : ''"
                  readonly placeholder="推算中"
                  class="computed-input"
                >
                  <template #suffix><span class="unit-suffix">MPa</span></template>
                </el-input>
              </el-form-item>
            </el-col>
          </el-row>

          <div v-if="store.fbCalcMode === 'calc'" class="estimation-panel">
            <div class="estimation-panel__title">
              28d 强度推算参数
              <span class="estimation-panel__formula">f<sub>b</sub> = γ<sub>f</sub> × γ<sub>s</sub> × γ<sub>b</sub> × γ<sub>SF</sub> × (γ<sub>c</sub> × f<sub>ce,g</sub>)</span>
            </div>

            <!-- Top bar: fce,g | γc | βc -->
            <el-row :gutter="16" style="margin-bottom:14px">
              <el-col :span="8">
                <el-form-item label="水泥强度等级 fce,g" class="small-label">
                  <el-select v-model="store.fceG" style="width:100%">
                    <el-option label="42.5" :value="42.5" />
                    <el-option label="52.5" :value="52.5" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item class="small-label">
                  <template #label>水泥富余系数 γ<sub>c</sub></template>
                  <el-input-number v-model="store.gammaC" :step="0.01" :min="1.0" :max="1.5" style="width:100%" />
                  <div class="param-hint">{{ gammaCHint }}</div>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item class="small-label">
                  <template #label>水泥质量分数 β<sub>c</sub></template>
                  <el-input :value="cementPct.toFixed(1)" readonly class="computed-input">
                    <template #suffix><span class="unit-suffix">%</span></template>
                  </el-input>
                  <div class="param-hint">= 100% − Σ(其他四组分)</div>
                </el-form-item>
              </el-col>
            </el-row>

            <!-- 4 material cards grid -->
            <div class="material-cards">
              <!-- 粉煤灰 -->
              <div class="material-card">
                <div class="material-card__head">粉煤灰</div>
                <div class="material-card__inputs">
                  <div class="mc-input">
                    <span class="mc-input__label">β<sub>1</sub></span>
                    <el-input-number :model-value="n(store.b1p)" @update:model-value="v => store.b1p = v ?? null" :min="0" :max="100" :step="1" :precision="1" placeholder="0" size="small" style="width:100%">
                      <template #suffix><span class="unit-suffix">%</span></template>
                    </el-input-number>
                  </div>
                  <div class="mc-input">
                    <span class="mc-input__label">γ<sub>f</sub></span>
                    <el-input-number v-model="store.gammaF" :step="0.01" :min="0.5" :max="1.2" size="small" style="width:100%" />
                  </div>
                </div>
                <dl class="ref-table">
                  <div><dt>0%</dt><dd>1.00</dd></div>
                  <div><dt>10%</dt><dd>0.90~1.00</dd></div>
                  <div><dt>20%</dt><dd>0.80~0.90</dd></div>
                  <div><dt>30%</dt><dd>0.70~0.80</dd></div>
                  <div><dt>40%</dt><dd>0.60~0.70</dd></div>
                </dl>
              </div>

              <!-- 矿粉 -->
              <div class="material-card">
                <div class="material-card__head">矿粉</div>
                <div class="material-card__inputs">
                  <div class="mc-input">
                    <span class="mc-input__label">β<sub>2</sub></span>
                    <el-input-number :model-value="n(store.b2p)" @update:model-value="v => store.b2p = v ?? null" :min="0" :max="100" :step="1" :precision="1" placeholder="0" size="small" style="width:100%">
                      <template #suffix><span class="unit-suffix">%</span></template>
                    </el-input-number>
                  </div>
                  <div class="mc-input">
                    <span class="mc-input__label">γ<sub>s</sub></span>
                    <el-input-number v-model="store.gammaS" :step="0.01" :min="0.5" :max="1.2" size="small" style="width:100%" />
                  </div>
                </div>
                <dl class="ref-table">
                  <div><dt>0%</dt><dd>1.00</dd></div>
                  <div><dt>10%</dt><dd>1.00</dd></div>
                  <div><dt>20%</dt><dd>0.95~1.00</dd></div>
                  <div><dt>30%</dt><dd>0.90~1.00</dd></div>
                  <div><dt>40%</dt><dd>0.80~0.90</dd></div>
                </dl>
              </div>

              <!-- 微珠 -->
              <div class="material-card">
                <div class="material-card__head">微珠</div>
                <div class="material-card__inputs">
                  <div class="mc-input">
                    <span class="mc-input__label">β<sub>3</sub></span>
                    <el-input-number :model-value="n(store.b3p)" @update:model-value="v => store.b3p = v ?? null" :min="0" :max="100" :step="1" :precision="1" placeholder="0" size="small" style="width:100%">
                      <template #suffix><span class="unit-suffix">%</span></template>
                    </el-input-number>
                  </div>
                  <div class="mc-input">
                    <span class="mc-input__label">γ<sub>b</sub></span>
                    <el-input-number v-model="store.gammaB" :step="0.01" :min="0.5" :max="1.2" size="small" style="width:100%" />
                  </div>
                </div>
                <dl class="ref-table">
                  <div><dt>0%</dt><dd>1.00</dd></div>
                  <div><dt>10%</dt><dd>0.95~1.05</dd></div>
                  <div><dt>20%</dt><dd>0.90~1.00</dd></div>
                  <div><dt>30%</dt><dd>0.85~0.95</dd></div>
                  <div><dt>40%</dt><dd>0.80~0.90</dd></div>
                </dl>
              </div>

              <!-- 硅灰 -->
              <div class="material-card">
                <div class="material-card__head">硅灰</div>
                <div class="material-card__inputs">
                  <div class="mc-input">
                    <span class="mc-input__label">β<sub>4</sub></span>
                    <el-input-number :model-value="n(store.b4p)" @update:model-value="v => store.b4p = v ?? null" :min="0" :max="100" :step="1" :precision="1" placeholder="0" size="small" style="width:100%">
                      <template #suffix><span class="unit-suffix">%</span></template>
                    </el-input-number>
                  </div>
                  <div class="mc-input">
                    <span class="mc-input__label">γ<sub>SF</sub></span>
                    <el-input-number v-model="store.gammaSF" :step="0.01" :min="0.5" :max="1.5" size="small" style="width:100%" />
                  </div>
                </div>
                <dl class="ref-table">
                  <div><dt>0%</dt><dd>1.00</dd></div>
                  <div><dt>5%</dt><dd>1.05~1.15</dd></div>
                  <div><dt>10%</dt><dd>1.10~1.25</dd></div>
                </dl>
              </div>
            </div>
          </div>
        </el-form>
      </div>
    </div>

    <!-- Section 2: 回归系数 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><TrendCharts /></el-icon>
        回归系数拟合
      </div>
      <div class="cs-section-body">
        <el-form label-position="top">
          <el-row :gutter="16" align="bottom">
            <el-col :span="5">
              <el-form-item >
<template #label>回归系数 α<sub>a</sub></template>
                <el-input-number v-model="store.aa" :step="0.01" :precision="4" style="width:100%" />
              </el-form-item>
            </el-col>
            <el-col :span="5">
              <el-form-item >
<template #label>回归系数 α<sub>b</sub></template>
                <el-input-number v-model="store.ab" :step="0.01" :precision="4" style="width:100%" />
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item >
<template #label>回归系数 α<sub>c</sub></template>
                <el-input-number v-model="store.ac" :step="0.1" :precision="4" style="width:100%" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="&nbsp;">
                <el-upload
                  :show-file-list="false"
                  accept=".csv,.xlsx,.xls"
                  :auto-upload="false"
                  :on-change="onFileChange"
                >
                  <el-button :loading="store.loading" plain>
                    <el-icon><Upload /></el-icon>
                    导入试验数据拟合
                  </el-button>
                </el-upload>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </div>
    </div>

    <!-- Section 3: 计算结果 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><Histogram /></el-icon>
        计算结果
      </div>
      <div class="cs-section-body">
        <el-form label-position="top">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item>
                <template #label>水胶比 (W/B)</template>
                <el-input
                  :value="store.wb ? store.wb.toFixed(4) : ''"
                  readonly placeholder="—"
                  class="computed-input wb-result"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>

        <el-alert type="info" :closable="false" style="margin-top:8px">
          <template #title>计算公式说明</template>
          <template #default>
            <Formula latex="f_{cu,0} = f_{cu,k} \times 1.15" style="margin-bottom:8px" />
            <Formula latex="W\!/\!B = \frac{\alpha_a \cdot f_b}{\,f_{cu,0} + \alpha_a \cdot \alpha_b \cdot f_b + \alpha_c\,}" />
            <p style="margin-top:8px;font-size:12px;color:#999">
              默认系数：α<sub>a</sub>=0.33，α<sub>b</sub>=1.09，α<sub>c</sub>=−49.54。
            </p>
          </template>
        </el-alert>

        <div class="footer-actions">
          <el-button type="primary" :disabled="!store.wb" @click="emit('next-step')">
            下一步
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wb-result :deep(.el-input__inner) {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 2px;
}

.estimation-panel {
  margin-top: 16px;
  padding: 16px;
  background: #f8faff;
  border: 1px dashed #c0cfeb;
  border-radius: 8px;
}

.estimation-panel__title {
  display: flex;
  align-items: center;
  font-size: 13px;
  font-weight: 700;
  color: #1e3c72;
  margin-bottom: 12px;
}

.estimation-panel__formula {
  margin-left: 12px;
  font-weight: normal;
  color: #5b6472;
  font-size: 12px;
  padding: 2px 8px;
  background: #eef4ff;
  border-radius: 4px;
}

.small-label :deep(.el-form-item__label) {
  font-size: 12px !important;
  color: #5b6472 !important;
}

.param-hint {
  font-size: 11px;
  color: #909399;
  margin-top: 4px;
}

.param-table {
  margin: 8px 0 0;
  font-size: 12px;
  color: #7b8394;
  line-height: 1.8;
  width: 100%;
}
.param-table div {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px dotted #dcdfe6;
  padding: 4px 6px;
  background: #fff;
}
.param-table div:last-child {
  border-bottom: none;
}
.param-table dt {
  font-weight: 600;
  color: #1e3c72;
  min-width: 40px;
}
.param-table dd {
  margin: 0;
  text-align: right;
  font-family: var(--el-font-family);
}

/* ── 4-card material grid ────────────────────────────────── */
.material-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.material-card {
  border: 1px solid #dbe5f1;
  border-radius: 10px;
  background: #fff;
  overflow: hidden;
}

.material-card__head {
  font-size: 13px;
  font-weight: 700;
  color: #1e3c72;
  padding: 8px 12px;
  background: #f4f7fc;
  border-bottom: 1px solid #e5e9f2;
  text-align: center;
}

.material-card__inputs {
  display: flex;
  gap: 8px;
  padding: 10px 10px 6px;
}

.mc-input {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.mc-input__label {
  font-size: 11px;
  font-weight: 600;
  color: #5b6472;
}

.ref-table {
  margin: 0;
  padding: 4px 10px 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
}

.ref-table div {
  font-size: 10px;
  background: #f8f9fc;
  padding: 2px 6px;
  border-radius: 3px;
  border-bottom: none;
  display: inline-flex;
  gap: 3px;
  white-space: nowrap;
}

.ref-table dt {
  font-weight: 600;
  color: #1e3c72;
}

.ref-table dd {
  margin: 0;
  color: #6b7280;
  text-align: left;
}
</style>
