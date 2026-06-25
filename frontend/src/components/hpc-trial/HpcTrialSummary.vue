<script setup lang="ts">
import { computed, ref } from 'vue'
import { useHpcTrialContext } from '../../composables/context'
import { formatKg, formatNullableNumber } from '../../utils/format'
import type { HpcTrialTab } from '../../composables/useHpcTrial'
import { useCalcStore } from '../../stores/calcStore'
import ImportDataSection from '../ImportDataSection.vue'

const props = defineProps<{
  activeTab: HpcTrialTab
}>()

const calcStore = useCalcStore()
const showImport = ref(false)

const {
  hasData,
  slumpMeasured,
  spreadMeasured,
  workabilityBinderDelta,
  workabilitySandRatioDelta,
  workabilityAlphaDelta,
  selectedWorkabilityReference,
  workabilityEvaluation,
  workabilityNote,
  workabilityResult,
  baseWb,
  baseBs,
  deltaWb,
  deltaBs,
  strengthMixes,
  strengthRegression,
  wbAdj,
  mbAdj,
  sandRatioAdj,
  alphaAdj,
  calculatedDensity,
  measuredDensity,
  densityCorrectionFactor,
  labMix,
} = useHpcTrialContext()

const fmt = formatNullableNumber
const fmtKg = formatKg

const strengthMixDisplayRows = computed(() => {
  const displayOrder = [1, 0, 2] as const

  return displayOrder.flatMap((sourceIndex) => {
    const mix = strengthMixes.value[sourceIndex]

    if (!mix) {
      return []
    }

    return [{
      mix,
      tagType: (sourceIndex === 0 ? 'primary' : sourceIndex === 1 ? 'success' : 'danger') as 'primary' | 'success' | 'danger',
      label: sourceIndex === 0 ? '基准' : sourceIndex === 1 ? '+Δ' : '-Δ',
    }]
  })
})

const headerTitle = computed(() => {
  if (props.activeTab === 'workability') {
    return '工作性汇总'
  }

  if (props.activeTab === 'strength') {
    return '强度汇总'
  }

  return '校正汇总'
})
</script>

<template>
  <el-card :body-style="{ padding: '16px' }" class="summary-card">
    <template #header>
      <div style="display: flex; align-items: center; gap: 6px; font-size: 15px; font-weight: 800; color: #2a5298">
        <el-icon><List /></el-icon>
        {{ headerTitle }}
      </div>
    </template>

    <template v-if="!hasData">
      <el-empty description="暂无数据，请先完成配合比计算" :image-size="80" />
    </template>

    <template v-else>
      <ImportDataSection v-model="showImport" :imported-values="calcStore.importedValues" category="hpc" />

      <template v-if="!showImport">
        <template v-if="activeTab === 'workability'">
      <div class="summary-group">
        <div class="group-label">试拌信息</div>
        <div class="summary-row">
          <span class="row-label">Vg 参考范围</span>
          <span class="row-val">{{ selectedWorkabilityReference ? selectedWorkabilityReference.desc : '未选择' }}</span>
        </div>
        <div class="summary-row">
          <span class="row-label">坍落度</span>
          <span class="row-val">{{ fmt(slumpMeasured) }} mm</span>
        </div>
        <div class="summary-row">
          <span class="row-label">扩展度</span>
          <span class="row-val">{{ fmt(spreadMeasured) }} mm</span>
        </div>
      </div>

      <div class="summary-group">
        <div class="group-label">调整量</div>
        <div class="summary-row">
          <span class="row-label">胶材调整 Δm<sub>b</sub></span>
          <span class="row-val">{{ workabilityBinderDelta.toFixed(2) }} kg/m³</span>
        </div>
        <div class="summary-row">
          <span class="row-label">砂率调整 Δβ<sub>s</sub></span>
          <span class="row-val">{{ workabilitySandRatioDelta.toFixed(2) }} %</span>
        </div>
        <div class="summary-row">
          <span class="row-label">外加剂调整 Δα</span>
          <span class="row-val">{{ workabilityAlphaDelta.toFixed(2) }} %</span>
        </div>
      </div>

      <div class="summary-group">
        <div class="group-label">调整后指标</div>
        <div class="summary-row">
          <span class="row-label">胶材用量 m<sub>b</sub></span>
          <span class="row-val" :class="{ changed: workabilityBinderDelta !== 0 }">{{ fmtKg(workabilityResult.mb) }}</span>
        </div>
        <div class="summary-row">
          <span class="row-label">砂率 β<sub>s</sub></span>
          <span class="row-val" :class="{ changed: workabilitySandRatioDelta !== 0 }">{{ fmt(workabilityResult.bs) }} %</span>
        </div>
        <div class="summary-row">
          <span class="row-label">外加剂掺量 α</span>
          <span class="row-val" :class="{ changed: workabilityAlphaDelta !== 0 }">{{ fmt(workabilityResult.alpha) }} %</span>
        </div>
        <div class="summary-row">
          <span class="row-label">固定 W/B</span>
          <span class="row-val">{{ fmt(workabilityResult.wb, 4) }}</span>
        </div>
      </div>

      <div class="summary-group">
        <div class="group-label">工作性评价</div>
        <div class="summary-row">
          <el-tag :type="workabilityEvaluation.tagType" size="small">
            {{ workabilityEvaluation.label }}
          </el-tag>
        </div>
        <div style="margin-top: 4px">
          <span style="font-size: 11px; color: #909399">{{ workabilityEvaluation.detail }}</span>
        </div>
        <div v-if="workabilityNote" style="margin-top: 4px">
          <span style="font-size: 11px; color: #909399">{{ workabilityNote }}</span>
        </div>
      </div>

      <div class="summary-total">
        <span class="total-label">每方合计</span>
        <span class="total-val">{{ workabilityResult.total ? workabilityResult.total.toFixed(2) + ' kg/m³' : '—' }}</span>
      </div>
    </template>

    <template v-else-if="activeTab === 'strength'">
      <div class="summary-group">
        <div class="group-label">实验参数</div>
        <div class="summary-row">
          <span class="row-label">基准 W/B</span>
          <span class="row-val">{{ fmt(baseWb, 4) }}</span>
        </div>
        <div class="summary-row">
          <span class="row-label">基准 β<sub>s</sub></span>
          <span class="row-val">{{ fmt(baseBs) }}%</span>
        </div>
        <div class="summary-row">
          <span class="row-label">ΔW/B</span>
          <span class="row-val">{{ deltaWb.toFixed(2) }}</span>
        </div>
        <div class="summary-row">
          <span class="row-label">Δβ<sub>s</sub></span>
          <span class="row-val">{{ deltaBs }}%</span>
        </div>
      </div>

      <div class="summary-group">
        <div class="group-label">三组水胶比</div>
        <div v-for="item in strengthMixDisplayRows" :key="item.mix.label" class="summary-row">
          <span class="row-label">
            <el-tag :type="item.tagType" size="small" style="font-size: 10px">
              {{ item.label }}
            </el-tag>
          </span>
          <span class="row-val">{{ fmt(item.mix.wb, 4) }}</span>
        </div>
      </div>

      <template v-if="strengthRegression">
        <div class="summary-group">
          <div class="group-label">回归结果</div>
          <div class="summary-row">
            <span class="row-label">R²</span>
            <span class="row-val">{{ (strengthRegression.r2 * 100).toFixed(1) }}%</span>
          </div>
          <div v-if="strengthRegression.recommendWb !== null" class="summary-row">
            <span class="row-label">推荐 W/B</span>
            <span class="row-val" style="color: #2a5298; font-size: 14px">{{ strengthRegression.recommendWb.toFixed(2) }}</span>
          </div>
          <div v-if="strengthRegression.predictStrength !== null" class="summary-row">
            <span class="row-label">推荐强度预测</span>
            <span class="row-val" style="color: #e6a23c">{{ strengthRegression.predictStrength.toFixed(1) }} MPa</span>
          </div>
        </div>
      </template>
    </template>

    <template v-else>
      <div class="summary-group">
        <div class="group-label">调整参数</div>
        <div class="summary-row">
          <span class="row-label">水胶比 W/B</span>
          <span class="row-val">{{ fmt(wbAdj, 4) }}</span>
        </div>
        <div class="summary-row">
          <span class="row-label">胶材用量 m<sub>b</sub></span>
          <span class="row-val">{{ fmtKg(mbAdj) }}</span>
        </div>
        <div class="summary-row">
          <span class="row-label">砂率 β<sub>s</sub></span>
          <span class="row-val">{{ fmt(sandRatioAdj) }}%</span>
        </div>
        <div class="summary-row">
          <span class="row-label">外加剂掺量 α</span>
          <span class="row-val">{{ fmt(alphaAdj) }}%</span>
        </div>
      </div>

      <div class="summary-group">
        <div class="group-label">表观密度校正</div>
        <div class="summary-row">
          <span class="row-label">计算值 ρ<sub>c,c</sub></span>
          <span class="row-val">{{ calculatedDensity ? calculatedDensity.toFixed(2) : '—' }} kg/m³</span>
        </div>
        <div class="summary-row">
          <span class="row-label">实测值 ρ<sub>c,t</sub></span>
          <span class="row-val">{{ measuredDensity ?? '—' }}{{ measuredDensity ? ' kg/m³' : '' }}</span>
        </div>
        <div class="summary-row">
          <span class="row-label">校正系数 δ</span>
          <span class="row-val" style="font-size: 14px; color: #2a5298">{{ densityCorrectionFactor ? densityCorrectionFactor.toFixed(6) : '—' }}</span>
        </div>
      </div>

      <div class="summary-total">
        <span class="total-label">实验室配合比合计</span>
        <span class="total-val">{{ labMix.total ? labMix.total.toFixed(2) + ' kg/m³' : '—' }}</span>
      </div>
      </template>
    </template>
    </template>
  </el-card>
</template>