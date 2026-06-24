<script setup lang="ts">
import { UHPC_INPUT_PLACEHOLDERS, useUhpcStore } from '../../stores/uhpcStore'
import '../../style/calc-tabs.css'

const emit = defineEmits<{
  (e: 'next-step'): void
}>()

const store = useUhpcStore()

const guideRows = [
  { grade: 130, label: 'UC130', range: '1.1 ~ 1.4' },
  { grade: 150, label: 'UC150', range: '1.0 ~ 1.3' },
]

function handleGuideSelect(grade: number) {
  store.strengthGrade = grade
}


</script>

<template>
  <div>
    <!-- S/B 参考范围 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><Grid /></el-icon>
        S/B 参考范围
      </div>
      <div class="cs-section-body">
        <div class="guide-table">
          <div class="guide-table__header">
            <span>抗压强度等级</span>
            <span>S/B</span>
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
            <span>{{ row.range }}</span>
          </button>
        </div>
        <el-alert type="info" :closable="false" style="margin-top:12px">
          <template #default>
            当 UHPC 的抗拉强度有应变硬化需求，或砂的压碎值大于 10% 时，砂胶比宜取偏小值；反之可取偏大值。
          </template>
        </el-alert>
      </div>
    </div>

    <!-- 砂胶比 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><EditPen /></el-icon>
        砂胶比输入
      </div>
      <div class="cs-section-body">
        <el-form label-position="top">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="砂胶比 (S/B)">
                <el-input-number
                  :model-value="store.sandBinderRatio ?? undefined"
                  @update:model-value="value => store.sandBinderRatio = value ?? null"
                  :min="0.5" :max="2" :step="0.05" :precision="2"
                  style="width:100%"
                />
                <div class="input-hint">参考值 {{ UHPC_INPUT_PLACEHOLDERS.sandBinderRatio }}</div>
                <div v-if="store.importedValueText('sand_ratio', '', 2) || store.importedValueText('sand_binder_ratio', '', 2)" class="input-hint">{{ store.importedValueText('sand_ratio', '', 2) || store.importedValueText('sand_binder_ratio', '', 2) }}</div>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
        <div class="footer-actions">
          <el-button type="primary" :disabled="store.sandBinderRatio === null" @click="emit('next-step')">
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
