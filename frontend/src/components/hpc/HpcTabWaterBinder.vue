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
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="水泥强度等级 fce,g" class="small-label">
                  <el-select v-model="store.fceG" style="width:100%">
                    <el-option label="42.5" :value="42.5" />
                    <el-option label="52.5" :value="52.5" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item  class="small-label">
<template #label>水泥富余系数 γ<sub>c</sub></template>
                  <el-input-number v-model="store.gammaC" :step="0.01" :min="1.0" :max="1.5" style="width:100%" />
                  <div class="param-hint">{{ gammaCHint }}</div>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item  class="small-label">
<template #label>粉煤灰影响系数 γ<sub>f</sub></template>
                  <el-input-number v-model="store.gammaF" :step="0.01" :min="0.5" :max="1.2" style="width:100%" />
                  <dl class="param-table">
                    <div><dt>0%</dt><dd>1.00</dd></div>
                    <div><dt>10%</dt><dd>0.90 ~ 1.00</dd></div>
                    <div><dt>20%</dt><dd>0.80 ~ 0.90</dd></div>
                    <div><dt>30%</dt><dd>0.70 ~ 0.80</dd></div>
                    <div><dt>40%</dt><dd>0.60 ~ 0.70</dd></div>
                  </dl>
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16" style="margin-top:12px">
              <el-col :span="8">
                <el-form-item  class="small-label">
<template #label>矿粉影响系数 γ<sub>s</sub></template>
                  <el-input-number v-model="store.gammaS" :step="0.01" :min="0.5" :max="1.2" style="width:100%" />
                  <dl class="param-table">
                    <div><dt>0%</dt><dd>1.00</dd></div>
                    <div><dt>10%</dt><dd>1.00</dd></div>
                    <div><dt>20%</dt><dd>0.95 ~ 1.00</dd></div>
                    <div><dt>30%</dt><dd>0.90 ~ 1.00</dd></div>
                    <div><dt>40%</dt><dd>0.80 ~ 0.90</dd></div>
                  </dl>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item  class="small-label">
<template #label>微珠影响系数 γ<sub>b</sub></template>
                  <el-input-number v-model="store.gammaB" :step="0.01" :min="0.5" :max="1.2" style="width:100%" />
                  <dl class="param-table">
                    <div><dt>0%</dt><dd>1.00</dd></div>
                    <div><dt>10%</dt><dd>0.95 ~ 1.05</dd></div>
                    <div><dt>20%</dt><dd>0.90 ~ 1.00</dd></div>
                    <div><dt>30%</dt><dd>0.85 ~ 0.95</dd></div>
                    <div><dt>40%</dt><dd>0.80 ~ 0.90</dd></div>
                  </dl>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item  class="small-label">
<template #label>硅灰影响系数 γ<sub>SF</sub></template>
                  <el-input-number v-model="store.gammaSF" :step="0.01" :min="0.5" :max="1.5" style="width:100%" />
                  <dl class="param-table">
                    <div><dt>0%</dt><dd>1.00</dd></div>
                    <div><dt>5%</dt><dd>1.05 ~ 1.15</dd></div>
                    <div><dt>10%</dt><dd>1.10 ~ 1.25</dd></div>
                  </dl>
                </el-form-item>
              </el-col>
            </el-row>
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
</style>
