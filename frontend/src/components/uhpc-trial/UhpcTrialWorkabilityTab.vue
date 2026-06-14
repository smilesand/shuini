<script setup lang="ts">
import type { UhpcTrialMixRowRes } from '../../api/calc'
import type { UhpcMaterialMasses } from '../../stores/uhpcStore'
import '../../style/calc-tabs.css'

const props = defineProps<{
  storeVal: (k: string) => number | null
  storeTotal: number | null
  sb: number
  alpha: number
  trialMix: UhpcTrialMixRowRes | null
  adjustedSB: number | null
  adjustedAlpha: number | null
  matKeys: readonly string[]
  matLabels: Record<string, string>
}>()

const emit = defineEmits<{
  (e: 'update:adjustedSB', v: number | null): void
  (e: 'update:adjustedAlpha', v: number | null): void
}>()

function fmt(v: number | null | undefined, d = 1): string {
  return v != null ? v.toFixed(d) : '—'
}
</script>

<template>
  <div>
    <!-- 计算配合比 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><Grid /></el-icon>
        计算配合比
      </div>
      <div class="cs-section-body">
        <p class="pane-lead">以配合比计算结果为基准，按需调整砂胶比和外加剂掺量，生成试拌配合比。</p>
        <div class="mix-label">每方用量 <span class="unit-tag">kg/m³</span></div>
        <div class="mix-grid mix-grid--calc">
          <div v-for="k in matKeys" :key="k" class="mix-cell">
            <div class="mix-cell__head">{{ matLabels[k] }}</div>
            <div class="mix-cell__val">{{ fmt(props.storeVal(k)) }}</div>
          </div>
          <div class="mix-cell mix-cell--total">
            <div class="mix-cell__head">合计</div>
            <div class="mix-cell__val">{{ fmt(storeTotal) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 试拌调整 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><Edit /></el-icon>
        试拌调整
      </div>
      <div class="cs-section-body">
        <el-row :gutter="32">
          <el-col :span="12">
            <el-form-item>
              <template #label>
                <span class="adj-label">砂胶比 (S/B)</span>
                <span class="adj-orig">计算值：{{ sb.toFixed(2) }}</span>
              </template>
              <el-input-number
                :model-value="adjustedSB ?? undefined"
                @update:model-value="v => emit('update:adjustedSB', v ?? null)"
                :min="0.5" :max="2" :step="0.05" :precision="2"
                :placeholder="sb.toFixed(2)"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item>
              <template #label>
                <span class="adj-label">外加剂掺量 α (%)</span>
                <span class="adj-orig">计算值：{{ alpha.toFixed(2) }}%</span>
              </template>
              <el-input-number
                :model-value="adjustedAlpha ?? undefined"
                @update:model-value="v => emit('update:adjustedAlpha', v ?? null)"
                :min="0" :max="10" :step="0.1" :precision="2"
                :placeholder="alpha.toFixed(2)"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
      </div>
    </div>

    <!-- 试拌配合比 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><DataAnalysis /></el-icon>
        试拌配合比
      </div>
      <div class="cs-section-body">
        <div class="mix-label">根据调整后的砂胶比和外加剂掺量重新计算 <span class="unit-tag">kg/m³</span></div>
        <div class="mix-grid mix-grid--trial">
          <div v-for="k in matKeys" :key="k" class="mix-cell">
            <div class="mix-cell__head">{{ matLabels[k] }}</div>
            <div class="mix-cell__val">{{ fmt(trialMix ? trialMix[k as keyof typeof trialMix] : null) }}</div>
          </div>
          <div class="mix-cell mix-cell--total">
            <div class="mix-cell__head">合计</div>
            <div class="mix-cell__val">{{ fmt(trialMix?.total) }}</div>
          </div>
        </div>
        <el-alert type="info" :closable="false" style="margin-top: 14px">
          水泥、粉煤灰、微珠、硅灰、砂的用量根据调整后的砂胶比和各自质量分数计算；
          外加剂用量根据调整后的胶材用量和外加剂掺量计算；钢纤维用量保持不变。
        </el-alert>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pane-lead { margin: 0 0 20px; font-size: 13px; color: #6b7280; line-height: 1.75; }
.adj-label { font-size: 13px; font-weight: 600; color: #374151; }
.adj-orig { display: inline-block; margin-left: 8px; font-size: 11px; color: #9ca3af; background: #e8eef6; border-radius: 4px; padding: 1px 6px; }
</style>
