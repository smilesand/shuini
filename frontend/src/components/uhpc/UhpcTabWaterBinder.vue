<script setup lang="ts">
import { computed } from 'vue'
import { UHPC_INPUT_PLACEHOLDERS, useUhpcStore } from '../../stores/uhpcStore'
import '../../style/calc-tabs.css'

const emit = defineEmits<{
  (e: 'next-step'): void
}>()

const store = useUhpcStore()

const designStrength = computed(() => store.designStrength)
const waterBinderPlaceholder = computed(() => (
  store.strengthGrade === 150 ? '0.17' : '0.19'
))

const guideRows = [
  { grade: 130, label: 'UC130', wb: '0.19 ± 0.01' },
  { grade: 150, label: 'UC150', wb: '0.17 ± 0.01' },
]

function handleGuideSelect(grade: number) {
  store.strengthGrade = grade

  if (store.waterBinderRatio === null) {
    store.waterBinderRatio = Number(grade === 150 ? '0.17' : '0.19')
  }

  if (store.admixtureRatio === null) {
    store.admixtureRatio = Number(UHPC_INPUT_PLACEHOLDERS.admixtureRatio)
  }
}


</script>

<template>
  <div>
    <!-- 强度等级与参考 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><DataAnalysis /></el-icon>
        强度等级与参考
      </div>
      <div class="cs-section-body">
        <el-form label-position="top">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item>
                <template #label>强度等级 f<sub>cu,k</sub></template>
                <el-input-number
                  :model-value="store.strengthGrade ?? undefined"
                  @update:model-value="value => store.strengthGrade = value ?? null"
                  :min="130" :step="20" :precision="0"
                  style="width:100%"
                >
                  <template #suffix><span class="unit-suffix">MPa</span></template>
                </el-input-number>
                <div class="input-hint">参考值 {{ UHPC_INPUT_PLACEHOLDERS.strengthGrade }} MPa</div>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item>
                <template #label>配制强度 f<sub>cu,0</sub></template>
                <el-input :model-value="designStrength !== null ? designStrength.toFixed(2) : ''" readonly class="computed-input">
                  <template #suffix><span class="unit-suffix">MPa</span></template>
                </el-input>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
        <div class="guide-table" style="margin-top:12px">
          <div class="guide-table__header">
            <span>抗压强度等级</span>
            <span>推荐 W/B</span>
          </div>
          <button
            v-for="row in guideRows"
            :key="row.grade"
            type="button"
            class="guide-table__row"
            :class="{ 'guide-table__row--active': store.strengthGrade === row.grade }"
            @click="handleGuideSelect(row.grade)"
          >
            <span>{{ row.label }}</span>
            <span>{{ row.wb }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 水胶比与外加剂 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><Drizzling /></el-icon>
        水胶比与外加剂
      </div>
      <div class="cs-section-body">
        <el-form label-position="top">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="水胶比 (W/B)">
                <el-input-number
                  :model-value="store.waterBinderRatio ?? undefined"
                  @update:model-value="value => store.waterBinderRatio = value ?? null"
                  :min="0.1" :max="0.5" :step="0.01" :precision="3"
                  style="width:100%"
                />
                <div class="input-hint">参考值 {{ waterBinderPlaceholder }}</div>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="外加剂掺量 α">
                <el-input-number
                  :model-value="store.admixtureRatio ?? undefined"
                  @update:model-value="value => store.admixtureRatio = value ?? null"
                  :min="0" :max="10" :step="0.1" :precision="2"
                  style="width:100%"
                >
                  <template #suffix><span class="unit-suffix">%</span></template>
                </el-input-number>
                <div class="input-hint">参考掺量 {{ UHPC_INPUT_PLACEHOLDERS.admixtureRatio }} %</div>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
        <div class="note-grid">
          <el-alert type="info" :closable="false">
            <template #title>W/B 取偏小值</template>
            <template #default>
              <div>1. 水泥 28d 抗压强度 &lt; 56 MPa</div>
              <div>2. 硅灰活性 &lt; 110%</div>
              <div>3. 砂压碎值 &gt; 10%</div>
            </template>
          </el-alert>
          <el-alert type="success" :closable="false">
            <template #title>W/B 取偏大值</template>
            <template #default>
              <div>1. 水泥 28d 抗压强度 &gt; 60 MPa</div>
              <div>2. 硅灰活性 &gt; 115%</div>
              <div>3. 砂压碎值 &lt; 7%</div>
            </template>
          </el-alert>
        </div>
        <div class="footer-actions">
          <el-button
            type="primary"
            :disabled="store.strengthGrade === null || store.waterBinderRatio === null || store.admixtureRatio === null"
            @click="emit('next-step')"
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
.note-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 14px;
}
</style>
