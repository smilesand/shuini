<script setup lang="ts">
import { watch } from 'vue'
import { useCalcStore } from '../../stores/calcStore.ts'
import { debounce } from '../../utils/debounce.ts'
import Formula from '../Formula.vue'
import '../../style/calc-tabs.css'

const emit = defineEmits<{ (e: 'next-step'): void }>()
const store = useCalcStore()

/** 将 number|null 转为 el-input-number 兼容的类型 */
const n = (v: number | null) => (v ?? undefined) as number | undefined

// 防抖计算：输入变化后 500ms 自动重算
const debouncedCalc = debounce(() => store.calcBinder(), 500)

watch(
  () => [
    store.b1p, store.rho1, store.b2p, store.rho2,
    store.b3p, store.rho3, store.b4p, store.rho4,
    store.rhoc, store.va,
    store.wb, store.mg, store.ms, store.rhog, store.rhos,
  ] as const,
  () => {
    if (store.rhoc && store.wb && store.mg && store.ms && store.rhog && store.rhos) {
      debouncedCalc()
    }
  },
)

async function handleNext() {
  await store.calcBinder()
  emit('next-step')
}
</script>

<template>
  <div>
    <!-- 依据参数 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><InfoFilled /></el-icon>
        依据参数
      </div>
      <div class="cs-section-body">
        <el-descriptions :column="3" size="small" border class="inherited-desc">
          <el-descriptions-item label="水胶比 (W/B)">
            <span class="inherited-val">{{ store.wb ? store.wb.toFixed(4) : '—' }}</span>
          </el-descriptions-item>
          <el-descriptions-item >
<template #label>粗骨料用量 m<sub>g</sub></template>
            <span class="inherited-val">{{ store.mg ? store.mg.toFixed(2) + ' kg' : '—' }}</span>
          </el-descriptions-item>
          <el-descriptions-item >
<template #label>细骨料用量 m<sub>s</sub></template>
            <span class="inherited-val">{{ store.ms ? store.ms.toFixed(2) + ' kg' : '—' }}</span>
          </el-descriptions-item>
        </el-descriptions>
        <el-alert
          v-if="!store.wb || !store.mg"
          title="请先完成水胶比和骨料计算"
          type="warning" show-icon :closable="false"
          style="margin-top:10px"
        />
      </div>
    </div>

    <!-- 胶凝材料组成 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><SetUp /></el-icon>
        胶凝材料组成
      </div>
      <div class="cs-section-body">
        <el-form label-position="top">
          <p style="font-size:12px;color:#909399;margin-bottom:12px">
            质量分数 β 请在 <b>水胶比页 → 28d强度推算参数</b> 中输入；密度 ρ 可在此直接修改。
          </p>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item >
<template #label>粉煤灰密度 ρ<sub>1</sub></template>
                <el-input-number :model-value="n(store.rho1)" @update:model-value="v => store.rho1 = v ?? null" :step="50" :precision="0" placeholder="" style="width:100%">
                  <template #suffix><span class="unit-suffix">kg/m³</span></template>
                </el-input-number>
                <div class="input-hint">参考值 2200 kg/m³</div>
                <div v-if="store.importedValueText('rho1', ' kg/m³', 0)" class="input-hint">{{ store.importedValueText('rho1', ' kg/m³', 0) }}</div>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item >
<template #label>粉煤灰质量分数 β<sub>1</sub></template>
                <el-input :value="store.b1p != null ? store.b1p.toFixed(1) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">%</span></template>
                </el-input>
                <div class="input-hint">在水胶比页 28d 推算参数中输入</div>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item >
<template #label>矿粉密度 ρ<sub>2</sub></template>
                <el-input-number :model-value="n(store.rho2)" @update:model-value="v => store.rho2 = v ?? null" :step="50" :precision="0" placeholder="" style="width:100%">
                  <template #suffix><span class="unit-suffix">kg/m³</span></template>
                </el-input-number>
                <div class="input-hint">参考值 2900 kg/m³</div>
                <div v-if="store.importedValueText('rho2', ' kg/m³', 0)" class="input-hint">{{ store.importedValueText('rho2', ' kg/m³', 0) }}</div>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item >
<template #label>矿粉质量分数 β<sub>2</sub></template>
                <el-input :value="store.b2p != null ? store.b2p.toFixed(1) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">%</span></template>
                </el-input>
                <div class="input-hint">在水胶比页 28d 推算参数中输入</div>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item >
<template #label>微珠密度 ρ<sub>3</sub></template>
                <el-input-number :model-value="n(store.rho3)" @update:model-value="v => store.rho3 = v ?? null" :step="50" :precision="0" placeholder="" style="width:100%">
                  <template #suffix><span class="unit-suffix">kg/m³</span></template>
                </el-input-number>
                <div class="input-hint">参考值 2100 kg/m³</div>
                <div v-if="store.importedValueText('rho3', ' kg/m³', 0)" class="input-hint">{{ store.importedValueText('rho3', ' kg/m³', 0) }}</div>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item >
<template #label>微珠质量分数 β<sub>3</sub></template>
                <el-input :value="store.b3p != null ? store.b3p.toFixed(1) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">%</span></template>
                </el-input>
                <div class="input-hint">在水胶比页 28d 推算参数中输入</div>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item >
<template #label>硅灰密度 ρ<sub>4</sub></template>
                <el-input-number :model-value="n(store.rho4)" @update:model-value="v => store.rho4 = v ?? null" :step="50" :precision="0" placeholder="" style="width:100%">
                  <template #suffix><span class="unit-suffix">kg/m³</span></template>
                </el-input-number>
                <div class="input-hint">参考值 2400 kg/m³</div>
                <div v-if="store.importedValueText('rho4', ' kg/m³', 0)" class="input-hint">{{ store.importedValueText('rho4', ' kg/m³', 0) }}</div>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item >
<template #label>硅灰质量分数 β<sub>4</sub></template>
                <el-input :value="store.b4p != null ? store.b4p.toFixed(1) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">%</span></template>
                </el-input>
                <div class="input-hint">在水胶比页 28d 推算参数中输入</div>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item >
<template #label>水泥密度 ρ<sub>c</sub></template>
                <el-input-number :model-value="n(store.rhoc)" @update:model-value="v => store.rhoc = v ?? null" :step="50" :precision="0" placeholder="" style="width:100%">
                  <template #suffix><span class="unit-suffix">kg/m³</span></template>
                </el-input-number>
                <div class="input-hint">参考值 3100 kg/m³</div>
                <div v-if="store.importedValueText('rhoc', ' kg/m³', 0)" class="input-hint">{{ store.importedValueText('rhoc', ' kg/m³', 0) }}</div>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item >
<template #label>含气量 V<sub>a</sub></template>
                <el-input-number :model-value="n(store.va)" @update:model-value="v => store.va = v ?? null" :min="0" :step="0.001" :precision="3" placeholder="" style="width:100%">
                  <template #suffix><span class="unit-suffix">m³</span></template>
                </el-input-number>
                <div class="input-hint">非引气混凝土参考 0.010</div>
                <div v-if="store.importedValueText('va', ' m³', 3) || store.importedValueText('air_content', ' m³', 3)" class="input-hint">{{ store.importedValueText('va', ' m³', 3) || store.importedValueText('air_content', ' m³', 3) }}</div>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </div>
    </div>

    <!-- 计算结果 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><Histogram /></el-icon>
        计算结果
      </div>
      <div class="cs-section-body">
        <el-form label-position="top">
          <p style="font-size:12px;color:#909399;margin-bottom:8px">中间量</p>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item >
<template #label>水泥质量分数 β<sub>c</sub></template>
                <el-input :value="store.bc ? (store.bc * 100).toFixed(1) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">%</span></template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item >
<template #label>胶凝材料密度 ρ<sub>b</sub></template>
                <el-input :value="store.rhob ? store.rhob.toFixed(1) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">kg/m³</span></template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item >
<template #label>浆体体积 V<sub>p</sub></template>
                <el-input :value="store.vp ? store.vp.toFixed(4) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">m³</span></template>
                </el-input>
              </el-form-item>
            </el-col>
          </el-row>
          <p style="font-size:12px;color:#909399;margin:12px 0 8px">各组分用量</p>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item >
<template #label>胶凝材料用量 m<sub>b</sub></template>
                <el-input :value="store.mb ? store.mb.toFixed(2) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">kg</span></template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item >
<template #label>粉煤灰用量 m<sub>1</sub></template>
                <el-input :value="store.m1 ? store.m1.toFixed(2) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">kg</span></template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item >
<template #label>矿粉用量 m<sub>2</sub></template>
                <el-input :value="store.m2 ? store.m2.toFixed(2) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">kg</span></template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item >
<template #label>微珠用量 m<sub>3</sub></template>
                <el-input :value="store.m3 ? store.m3.toFixed(2) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">kg</span></template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item >
<template #label>硅灰用量 m<sub>4</sub></template>
                <el-input :value="store.m4 ? store.m4.toFixed(2) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">kg</span></template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item >
<template #label>水泥用量 m<sub>c</sub></template>
                <el-input :value="store.mc ? store.mc.toFixed(2) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">kg</span></template>
                </el-input>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>

        <el-alert type="info" :closable="false" style="margin-top:8px">
          <template #title>计算公式说明</template>
          <template #default>
            <Formula latex="\beta_c = 1 - \beta_1 - \beta_2 - \beta_3 - \beta_4" style="margin-bottom:8px" />
            <Formula latex="\rho_b = \frac{1}{\frac{\beta_1}{\rho_1} + \frac{\beta_2}{\rho_2} + \frac{\beta_3}{\rho_3} + \frac{\beta_4}{\rho_4} + \frac{\beta_c}{\rho_c}}" style="margin-bottom:8px" />
            <Formula latex="V_p = 1 - \frac{m_g}{\rho_g} - \frac{m_s}{\rho_s}" style="margin-bottom:8px" />
            <Formula latex="m_b = \frac{V_p - V_a}{\frac{1}{\rho_b} + \frac{W/B}{\rho_w}}" style="margin-bottom:8px" />
            <Formula latex="m_i = m_b \times \beta_i \quad (i = 1,2,3,4,c)" />
          </template>
        </el-alert>

        <div class="footer-actions">
          <el-button
            type="primary"
            :loading="store.loading"
            :disabled="!store.wb || !store.mg || !store.ms || !store.rhoc"
            @click="handleNext"
          >
            下一步
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* No local styles needed — all shared via calc-tabs.css */
</style>
