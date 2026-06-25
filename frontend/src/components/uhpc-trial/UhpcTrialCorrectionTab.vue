<script setup lang="ts">
import { computed } from 'vue'
import type { UhpcTrialMixRowRes } from '../../api/calc'
import StrengthEvalCard from '../StrengthEvalCard.vue'
import type { StrengthGroup } from '../../composables/useStrengthEval'
import { computeGroupValue } from '../../composables/useStrengthEval'
import '../../style/calc-tabs.css'

const props = defineProps<{
  corrBase: 'trial' | 'wbRec' | 'sfRec'
  recWb: number | null
  recSf: number | null
  matKeys: readonly string[]
  matLabels: Record<string, string>
  corrMix: UhpcTrialMixRowRes | null
  measuredDensity: number | null
  calcDensity: number | null
  corrFactor: number | null
  needsCorr: boolean
  labMix: UhpcTrialMixRowRes | null
  designStr: number
  strengthGrade: number | null
  strengthGroups: StrengthGroup[]
  evalSpread: number | null
  evalSpreadReq: number | null
  evalWorkabilityDesc: string
}>()

const emit = defineEmits<{
  (e: 'update:corrBase', v: 'trial' | 'wbRec' | 'sfRec'): void
  (e: 'update:measuredDensity', v: number | null): void
  (e: 'update:strengthGroups', v: StrengthGroup[]): void
  (e: 'update:evalSpread', v: number | null): void
  (e: 'update:evalSpreadReq', v: number | null): void
  (e: 'update:evalWorkabilityDesc', v: string): void
}>()

function fmt(v: number | null | undefined, d = 1): string {
  return v != null ? v.toFixed(d) : '—'
}

// ── Spread evaluation ──────────────────────────────────────────
const spreadEval = computed(() => {
  const measured = props.evalSpread
  const req = props.evalSpreadReq
  if (measured === null || req === null) {
    return { status: 'pending' as const, label: '待评价', tagType: 'info' as const, detail: '请填写实测扩展度和扩展度要求。' }
  }
  const lo = req - 50
  const hi = req + 50
  const pass = measured >= lo && measured <= hi
  return {
    status: pass ? ('pass' as const) : ('fail' as const),
    label: pass ? '合格' : '不合格',
    tagType: pass ? ('success' as const) : ('danger' as const),
    detail: pass
      ? `扩展度 ${measured} mm 在 ${req}±50 mm 范围内 (${lo}–${hi} mm)`
      : `扩展度 ${measured} mm 不在 ${req}±50 mm 范围内 (${lo}–${hi} mm)`,
  }
})

// ── Group-based 28d strength evaluation ─────────────────────────
const groupResults = computed(() =>
  props.strengthGroups.map(g => computeGroupValue(g.values)),
)

const overallAvg = computed<number | null>(() => {
  const vals = groupResults.value.map(r => r.value).filter((v): v is number => v !== null)
  if (vals.length === 0) return null
  return vals.reduce((s, v) => s + v, 0) / vals.length
})

const minGroupAvg = computed<number | null>(() => {
  const vals = groupResults.value.map(r => r.value).filter((v): v is number => v !== null)
  if (vals.length === 0) return null
  return Math.min(...vals)
})

const allComplete = computed(() =>
  groupResults.value.length >= 6 && groupResults.value.every(r => r.value !== null),
)

const strengthEvaluation = computed(() => {
  const target = props.designStr
  const ov = overallAvg.value
  const minG = minGroupAvg.value
  const sg = props.strengthGrade

  if (target === null || !Number.isFinite(target)) {
    return {
      status: 'pending' as const,
      label: '待评价',
      tagType: 'info' as const,
      detail: '请先在主计算页完成配制强度计算。',
    }
  }

  if (!allComplete.value || ov === null) {
    return {
      status: 'pending' as const,
      label: '待输入',
      tagType: 'info' as const,
      detail: '请完成所有 6 组（每组 3 条）28d 抗压强度数据填写。',
    }
  }

  const overallPass = ov >= target
  const minThreshold = sg !== null && Number.isFinite(sg) ? sg * 0.95 : null
  const minGroupPass = minThreshold !== null && minG !== null ? minG >= minThreshold : null
  const allPass = overallPass && (minGroupPass !== false)

  let detail = `总体平均值 ${ov.toFixed(1)} MPa`
  detail += overallPass
    ? ` ≥ 配制强度 ${target.toFixed(1)} MPa`
    : ` < 配制强度 ${target.toFixed(1)} MPa，差值 ${(target - ov).toFixed(1)} MPa`

  if (minThreshold !== null && minG !== null) {
    detail += `；组均值最小值 ${minG.toFixed(1)} MPa`
    detail += minGroupPass
      ? ` ≥ 0.95×强度等级(${minThreshold.toFixed(1)} MPa)`
      : ` < 0.95×强度等级(${minThreshold.toFixed(1)} MPa)`
  }

  return {
    status: allPass ? ('pass' as const) : ('fail' as const),
    label: allPass ? '合格' : '不合格',
    tagType: allPass ? ('success' as const) : ('danger' as const),
    detail,
  }
})
</script>

<template>
  <div>
    <!-- 调整配合比基准 — 卡片选择模式 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><SetUp /></el-icon>
        选择调整配合比基准
      </div>
      <div class="cs-section-body">
        <div class="base-cards">
          <!-- 试拌配合比 -->
          <div
            class="base-card"
            :class="{ 'base-card--active': corrBase === 'trial' }"
            @click="emit('update:corrBase', 'trial')"
          >
            <div class="base-card__icon"><el-icon><Van /></el-icon></div>
            <div class="base-card__title">试拌配合比</div>
            <div class="base-card__desc">以工作性试验中的试拌调整结果为基准，进行配合比校正</div>
            <div v-if="corrBase === 'trial'" class="base-card__badge">当前选择</div>
          </div>

          <!-- 推荐水胶比 -->
          <div
            class="base-card"
            :class="{ 'base-card--active': corrBase === 'wbRec', 'base-card--disabled': recWb === null }"
            @click="recWb !== null && emit('update:corrBase', 'wbRec')"
          >
            <div class="base-card__icon"><el-icon><TrendCharts /></el-icon></div>
            <div class="base-card__title">推荐水胶比配合比</div>
            <div class="base-card__desc">
              基于强度回归推荐的胶水比
              <template v-if="recWb !== null">（W/B = {{ recWb.toFixed(3) }}）</template>
              <template v-else>（需先在强度试验页填入数据）</template>
            </div>
            <div v-if="corrBase === 'wbRec'" class="base-card__badge">当前选择</div>
          </div>

          <!-- 推荐硅灰 -->
          <div
            class="base-card"
            :class="{ 'base-card--active': corrBase === 'sfRec', 'base-card--disabled': recSf === null }"
            @click="recSf !== null && emit('update:corrBase', 'sfRec')"
          >
            <div class="base-card__icon"><el-icon><DataAnalysis /></el-icon></div>
            <div class="base-card__title">推荐硅灰配合比</div>
            <div class="base-card__desc">
              基于强度回归推荐的硅灰用量
              <template v-if="recSf !== null">（硅灰 {{ recSf.toFixed(1) }} kg）</template>
              <template v-else>（需先在强度试验页填入数据）</template>
            </div>
            <div v-if="corrBase === 'sfRec'" class="base-card__badge">当前选择</div>
          </div>
        </div>

        <div class="mix-label" style="margin-top:14px">调整配合比 <span class="unit-tag">kg/m³</span></div>
        <div v-if="corrMix" class="mix-grid mix-grid--trial" style="grid-template-columns: repeat(10, 1fr);">
          <div v-for="k in matKeys" :key="k" class="mix-cell">
            <div class="mix-cell__head">{{ matLabels[k] }}</div>
            <div class="mix-cell__val">{{ fmt(corrMix[k as keyof typeof corrMix]) }}</div>
          </div>
          <div class="mix-cell">
            <div class="mix-cell__head">外加剂掺量(%)</div>
            <div class="mix-cell__val">{{ corrMix.admixture_pct !== undefined && corrMix.admixture_pct !== 0 ? fmt(corrMix.admixture_pct, 2) + '%' : '—' }}</div>
          </div>
          <div class="mix-cell mix-cell--total">
            <div class="mix-cell__head">合计</div>
            <div class="mix-cell__val">{{ fmt(corrMix.total) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 密度校正 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><Odometer /></el-icon>
        表观密度校正
      </div>
      <div class="cs-section-body">
        <el-row :gutter="20" style="margin-bottom: 12px">
          <el-col :span="8">
            <div class="density-field">
              <div class="density-field__label">拌合物表观密度实测值</div>
              <el-input-number
                :model-value="measuredDensity ?? undefined"
                @update:model-value="v => emit('update:measuredDensity', v ?? null)"
                :min="1500" :max="3500" :step="10" :precision="0"
                placeholder=""
                style="width: 100%"
              />
              <div class="density-field__unit">kg/m³</div>
              <div class="input-hint">参考值 2510 kg/m³</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="density-field">
              <div class="density-field__label">拌合物表观密度计算值</div>
              <el-input :value="fmt(calcDensity)" readonly class="calc-inp" />
              <div class="density-field__unit">kg/m³</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="density-field">
              <div class="density-field__label">校正系数 k</div>
              <el-input
                :value="corrFactor !== null ? corrFactor.toFixed(4) : '—'"
                readonly class="calc-inp"
              />
              <div class="density-field__unit">实测 / 计算</div>
            </div>
          </el-col>
        </el-row>
        <div
          v-if="corrFactor !== null"
          class="corr-status"
          :class="needsCorr ? 'corr-status--warn' : 'corr-status--ok'"
        >
          <el-icon :size="16">
            <component :is="needsCorr ? 'Warning' : 'CircleCheck'" />
          </el-icon>
          <span v-if="needsCorr">
            偏差 {{ (Math.abs((measuredDensity ?? 0) - (calcDensity ?? 0)) / (calcDensity ?? 1) * 100).toFixed(2) }}%
            已超过 2%，实验室配合比已乘以校正系数 <b>{{ corrFactor.toFixed(4) }}</b>。
          </span>
          <span v-else>偏差未超过 2%，实验室配合比维持调整配合比不变。</span>
        </div>
      </div>
    </div>

    <!-- 实验室配合比 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><DocumentChecked /></el-icon>
        实验室配合比
      </div>
      <div class="cs-section-body">
        <template v-if="labMix">
          <div class="mix-label" style="margin-bottom:8px">
            <span class="unit-tag">kg/m³{{ needsCorr ? '（已按校正系数调整）' : '' }}</span>
          </div>
          <div class="mix-grid" :class="needsCorr ? 'mix-grid--corrected' : 'mix-grid--trial'" style="grid-template-columns: repeat(10, 1fr);">
            <div v-for="k in matKeys" :key="k" class="mix-cell">
              <div class="mix-cell__head">{{ matLabels[k] }}</div>
              <div class="mix-cell__val">{{ fmt(labMix[k as keyof typeof labMix]) }}</div>
            </div>
            <div class="mix-cell">
              <div class="mix-cell__head">外加剂掺量(%)</div>
              <div class="mix-cell__val">{{ labMix.admixture_pct !== undefined && labMix.admixture_pct !== 0 ? fmt(labMix.admixture_pct, 2) + '%' : '—' }}</div>
            </div>
            <div class="mix-cell mix-cell--total">
              <div class="mix-cell__head">合计</div>
              <div class="mix-cell__val">{{ fmt(labMix.total) }}</div>
            </div>
          </div>
        </template>
        <el-alert
          v-else
          type="warning"
          :closable="false"
          title="请录入实测表观密度以生成实验室配合比。"
          style="margin-bottom: 12px"
        />
        <el-alert type="info" :closable="false" style="margin-top: 14px">
          <b>注：</b>
          实测值与计算值之差的绝对值不超过计算值的 2%，则维持调整配合比，即为实验室配合比；
          超过 2%，各材料用量均需乘以校正系数（k = 实测值 / 计算值）。
        </el-alert>
      </div>
    </div>

    <!-- 工作性与性能评价 (UHPC) -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><DataAnalysis /></el-icon>
        混凝土性能及评价（实验室配合比）
      </div>
      <div class="cs-section-body">
        <!-- 28d抗压强度分组试验数据 -->
        <StrengthEvalCard
          :groups="strengthGroups"
          :target-strength="designStr"
          :strength-grade="strengthGrade"
          :strength-multiplier="1.10"
          @update:groups="v => emit('update:strengthGroups', v)"
        />

        <el-divider style="margin: 20px 0" />

        <el-form label-position="top" size="default">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item>
                <template #label>实测扩展度</template>
                <el-input-number
                  :model-value="evalSpread ?? undefined"
                  @update:model-value="v => emit('update:evalSpread', v ?? null)"
                  :min="0" :max="900" :step="5"
                  placeholder=""
                  style="width: 100%"
                >
                  <template #suffix><span class="unit-suffix">mm</span></template>
                </el-input-number>
                <div class="input-hint">参考值 650 mm</div>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item>
                <template #label>扩展度要求</template>
                <el-input-number
                  :model-value="evalSpreadReq ?? undefined"
                  @update:model-value="v => emit('update:evalSpreadReq', v ?? null)"
                  :min="0" :max="900" :step="5"
                  placeholder=""
                  style="width: 100%"
                >
                  <template #suffix><span class="unit-suffix">mm</span></template>
                </el-input-number>
                <div class="input-hint">评判依据：扩展度 ±50 mm</div>
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="20">
            <el-col :span="24">
              <el-form-item>
                <template #label>工作性综合描述</template>
                <el-input
                  type="textarea"
                  :rows="3"
                  :model-value="evalWorkabilityDesc"
                  @update:model-value="v => emit('update:evalWorkabilityDesc', v)"
                  placeholder=""
                />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>

        <div style="display:flex;align-items:center;gap:12px;margin-top:16px;">
          <span style="font-weight:bold;color:#374151;font-size:13px;">性能评价：</span>
          <span style="font-size:12px;color:#6b7280;">强度</span>
          <el-tag :type="strengthEvaluation.tagType" size="small">{{ strengthEvaluation.label }}</el-tag>
          <span style="font-size:12px;color:#6b7280;">{{ strengthEvaluation.detail }}</span>
          <span style="font-size:12px;color:#6b7280;margin-left:8px;">扩展度</span>
          <el-tag :type="spreadEval.tagType" size="small">{{ spreadEval.label }}</el-tag>
          <span style="font-size:12px;color:#6b7280;">{{ spreadEval.detail }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ── Base cards ───────────────────────────────────────────────── */
.base-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.base-card {
  position: relative;
  padding: 20px 16px;
  border-radius: 12px;
  border: 2px solid #e5e9f2;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: center;
}

.base-card:hover {
  border-color: #94b4e0;
  box-shadow: 0 2px 12px rgba(30, 60, 114, 0.08);
}

.base-card--active {
  border-color: #1e3c72;
  background: linear-gradient(135deg, #f0f5ff, #e8effb);
  box-shadow: 0 2px 16px rgba(30, 60, 114, 0.12);
}

.base-card--disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.base-card--disabled:hover {
  border-color: #e5e9f2;
  box-shadow: none;
}

.base-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: #f0f4fa;
  color: #1e3c72;
  font-size: 20px;
  margin-bottom: 12px;
}

.base-card--active .base-card__icon {
  background: linear-gradient(135deg, #1e3c72, #2a5298);
  color: #fff;
}

.base-card__title {
  font-size: 14px;
  font-weight: 700;
  color: #374151;
  margin-bottom: 8px;
}

.base-card--active .base-card__title {
  color: #1e3c72;
}

.base-card__desc {
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.6;
}

.base-card__badge {
  position: absolute;
  top: -8px;
  right: -8px;
  padding: 3px 10px;
  border-radius: 999px;
  background: linear-gradient(135deg, #1e3c72, #2a5298);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.05em;
}

/* ── Density fields ───────────────────────────────────────────── */
.density-field { display: flex; flex-direction: column; gap: 6px; }
.density-field__label { font-size: 13px; font-weight: 600; color: #374151; }
.density-field__unit { font-size: 11px; color: #9ca3af; }
.calc-inp :deep(.el-input__wrapper) { background: linear-gradient(135deg, #fff8ec, #ffedcc); }
.calc-inp :deep(.el-input__inner) { color: #7a4300; font-weight: 800; text-align: center; }

/* ── Correction status ────────────────────────────────────────── */
.corr-status { display: flex; align-items: flex-start; gap: 8px; padding: 12px 16px; border-radius: 10px; font-size: 13px; line-height: 1.6; margin-top: 12px; }
.corr-status--warn { background: #fff3cd; border: 1px solid #f5c842; color: #856404; }
.corr-status--ok { background: #d1e7dd; border: 1px solid #82c88a; color: #0f5132; }
</style>
