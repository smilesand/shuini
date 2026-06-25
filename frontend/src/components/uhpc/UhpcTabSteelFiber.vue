<script setup lang="ts">
import { computed } from 'vue'
import { UHPC_INPUT_PLACEHOLDERS, type FiberStrengthGrade, useUhpcStore } from '../../stores/uhpcStore'
import '../../style/calc-tabs.css'

const emit = defineEmits<{
  (e: 'next-step'): void
}>()

const store = useUhpcStore()

const guideRows: Array<{
  grade: FiberStrengthGrade
  label: string
  range: string
}> = [
  { grade: 'UT05', label: 'UT05', range: '1.5% ± 0.3%' },
  { grade: 'UT07', label: 'UT07', range: '2.0% ± 0.3%' },
]

function handleGuideSelect(grade: FiberStrengthGrade) {
  store.fiberStrengthGrade = grade
}

const steelFiberMassPreview = computed(() => {
  if (store.steelFiberVolumeRatio === null) {
    return null
  }

  return (store.steelFiberVolumeRatio / 100) * store.steelFiberDensity
})
</script>

<template>
  <div>
    <!-- 钢纤维参考 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><Histogram /></el-icon>
        钢纤维参考
      </div>
      <div class="cs-section-body">
        <div class="guide-table">
          <div class="guide-table__header">
            <span>抗拉强度等级</span>
            <span>体积掺量参考</span>
          </div>
          <button
            v-for="row in guideRows"
            :key="row.grade"
            type="button"
            class="guide-table__row"
            :class="{ 'guide-table__row--active': store.fiberStrengthGrade === row.grade }"
            @click="handleGuideSelect(row.grade)"
          >
            <span>{{ row.label }}</span>
            <span>{{ row.range }}</span>
          </button>
        </div>
        <el-alert type="info" :closable="false" style="margin-top:12px">
          <template #default>
            当 UHPC 的抗拉强度有应变硬化需求时，钢纤维体积掺量可取偏大值；当抗拉强度未达到设计要求时，应适当增加钢纤维用量。
          </template>
        </el-alert>
      </div>
    </div>

    <!-- 钢纤维用量 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><EditPen /></el-icon>
        钢纤维用量
      </div>
      <div class="cs-section-body">
        <el-form label-position="top">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item>
                <template #label>钢纤维体积掺量 V<sub>f</sub></template>
                <el-input-number
                  :model-value="store.steelFiberVolumeRatio ?? undefined"
                  @update:model-value="value => store.steelFiberVolumeRatio = value ?? null"
                  :min="0" :max="5" :step="0.1" :precision="2"
                  style="width:100%"
                >
                  <template #suffix><span class="unit-suffix">%</span></template>
                </el-input-number>
                <div class="input-hint">参考值 {{ UHPC_INPUT_PLACEHOLDERS.steelFiberVolumeRatio }} %</div>
                <div v-if="store.importedValueText('steel_fiber_volume_ratio', ' %', 2)" class="input-hint">{{ store.importedValueText('steel_fiber_volume_ratio', ' %', 2) }}</div>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item>
                <template #label>折算钢纤维质量 m<sub>f</sub></template>
                <el-input :model-value="steelFiberMassPreview !== null ? steelFiberMassPreview.toFixed(2) : ''" readonly class="computed-input">
                  <template #suffix><span class="unit-suffix">kg/m³</span></template>
                </el-input>
                <div v-if="store.importedValueText('steel_fiber', ' kg/m³', 2) || store.importedValueText('msf', ' kg/m³', 2)" class="input-hint">{{ store.importedValueText('steel_fiber', ' kg/m³', 2) || store.importedValueText('msf', ' kg/m³', 2) }}</div>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
        <div class="footer-actions">
          <el-button type="primary" :disabled="store.steelFiberVolumeRatio === null" @click="emit('next-step')">
            下一步
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* No local styles needed */
</style>
