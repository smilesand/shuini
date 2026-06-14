<script setup lang="ts">
import type { UhpcTrialMixRowRes } from '../../api/calc'
import '../../style/calc-tabs.css'

const props = defineProps<{
  wb: number
  designStr: number
  strengthGrade: number | null
  matKeys: readonly string[]
  matLabels: Record<string, string>
  trialMix: UhpcTrialMixRowRes | null
  sWb0: number | null
  variants: {
    label: string
    tagCls: string
    mix: UhpcTrialMixRowRes | null
    sRef: { value: number | null }
    aRef: { value: number | null }
  }[]
  vSfPlus: UhpcTrialMixRowRes | null
  vSfMinus: UhpcTrialMixRowRes | null
  sWbPlus: number | null
  sWbMinus: number | null
  sSfPlus: number | null
  sSfMinus: number | null
  recWb: number | null
  recSf: number | null
}>()

const emit = defineEmits<{
  (e: 'update:sWb0', v: number | null): void
}>()

function fmt(v: number | null | undefined, d = 1): string {
  return v != null ? v.toFixed(d) : '—'
}
</script>

<template>
  <div>
    <!-- 基准配合比 -->
    <div v-if="trialMix" class="cs-section">
      <div class="cs-section-head">
        <el-icon><Collection /></el-icon>
        基准配合比（来自工作性试验试拌结果）
      </div>
      <div class="cs-section-body">
        <p class="pane-lead">
          以下为工作性试验确定的试拌配合比。W/B = <b>{{ wb.toFixed(3) }}</b>，硅灰 = <b>{{ trialMix.silica_fume.toFixed(1) }} kg</b>。
          填入实测 28d 抗压强度后，系统将与下方变体共同进行线性回归分析，推荐最优参数。
        </p>
        <div class="variant-list">
          <div class="variant-row variant-row--base">
            <div class="vrow-tag tag--base">
              基准
              <div class="tag-extra">W/B {{ wb.toFixed(3) }}</div>
              <div class="tag-extra">SF {{ trialMix.silica_fume.toFixed(1) }} kg</div>
            </div>
            <div class="vrow-mix">
              <div class="mix-grid mix-grid--variant">
                <div v-for="k in matKeys" :key="k" class="mix-cell mix-cell--sm">
                  <div class="mix-cell__head">{{ matLabels[k] }}</div>
                  <div class="mix-cell__val">{{ fmt(trialMix[k as keyof typeof trialMix] as number | null) }}</div>
                </div>
                <div class="mix-cell mix-cell--sm mix-cell--total">
                  <div class="mix-cell__head">合计</div>
                  <div class="mix-cell__val">{{ fmt(trialMix.total) }}</div>
                </div>
              </div>
            </div>
            <div class="vrow-input">
              <el-input-number
                :model-value="sWb0 ?? undefined"
                @update:model-value="v => emit('update:sWb0', v ?? null)"
                :min="0" :max="400" :step="1" :precision="1"
                placeholder="实测强度"
                style="width: 160px"
              />
              <span class="unit-s">MPa</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 强度试验配合比 — 水胶比组 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><TrendCharts /></el-icon>
        水胶比试验组（基准 W/B={{ wb.toFixed(3) }}，步长 ±0.01）
      </div>
      <div class="cs-section-body">
        <p class="pane-lead">
          以试拌配合比为基准，调整水胶比（±0.01），保持其他参数不变。测定各组 28d 抗压强度，系统将基于三点数据进行线性回归推荐最优水胶比。
        </p>
        <div class="variant-list">
          <div v-for="(v, i) in variants.filter(v => v.tagCls === 'tag--wb')" :key="i" class="variant-row">
            <div class="vrow-tag" :class="v.tagCls">{{ v.label }}</div>
            <div class="vrow-mix">
              <div class="mix-grid mix-grid--variant">
                <div v-for="k in matKeys" :key="k" class="mix-cell mix-cell--sm">
                  <div class="mix-cell__head">{{ matLabels[k] }}</div>
                  <div v-if="k === 'admixture'" class="mix-cell__val mix-cell__val--input">
                    <el-input-number
                      :model-value="v.aRef.value ?? undefined"
                      @update:model-value="val => v.aRef.value = val ?? null"
                      :min="0" :max="100" :step="0.1" :precision="1"
                      placeholder="调整"
                      size="small"
                      controls-position="right"
                      style="width: 90px"
                    />
                  </div>
                  <div v-else class="mix-cell__val">{{ fmt(v.mix ? v.mix[k as keyof typeof v.mix] : null) }}</div>
                </div>
                <div class="mix-cell mix-cell--sm mix-cell--total">
                  <div class="mix-cell__head">合计</div>
                  <div class="mix-cell__val">{{ fmt(v.mix ? v.mix.total : null) }}</div>
                </div>
              </div>
            </div>
            <div class="vrow-input">
              <el-input-number
                :model-value="v.sRef.value ?? undefined"
                @update:model-value="val => v.sRef.value = val ?? null"
                :min="0" :max="400" :step="1" :precision="1"
                placeholder="实测强度"
                style="width: 160px"
              />
              <span class="unit-s">MPa</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 强度试验配合比 — 硅灰组 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><DataAnalysis /></el-icon>
        硅灰用量试验组（基准 SF={{ trialMix ? trialMix.silica_fume.toFixed(1) : '—' }} kg，步长 ±5%）
      </div>
      <div class="cs-section-body">
        <p class="pane-lead">
          以试拌配合比为基准，调整硅灰用量（±5% 胶材占比），保持水胶比不变。测定各组 28d 抗压强度，系统将基于三点数据进行线性回归推荐最优硅灰用量。
        </p>
        <div class="variant-list">
          <div v-for="(v, i) in variants.filter(v => v.tagCls === 'tag--sf')" :key="i" class="variant-row">
            <div class="vrow-tag" :class="v.tagCls">{{ v.label }}</div>
            <div class="vrow-mix">
              <div class="mix-grid mix-grid--variant">
                <div v-for="k in matKeys" :key="k" class="mix-cell mix-cell--sm">
                  <div class="mix-cell__head">{{ matLabels[k] }}</div>
                  <div v-if="k === 'admixture'" class="mix-cell__val mix-cell__val--input">
                    <el-input-number
                      :model-value="v.aRef.value ?? undefined"
                      @update:model-value="val => v.aRef.value = val ?? null"
                      :min="0" :max="100" :step="0.1" :precision="1"
                      placeholder="调整"
                      size="small"
                      controls-position="right"
                      style="width: 90px"
                    />
                  </div>
                  <div v-else class="mix-cell__val">{{ fmt(v.mix ? v.mix[k as keyof typeof v.mix] : null) }}</div>
                </div>
                <div class="mix-cell mix-cell--sm mix-cell--total">
                  <div class="mix-cell__head">合计</div>
                  <div class="mix-cell__val">{{ fmt(v.mix ? v.mix.total : null) }}</div>
                </div>
              </div>
            </div>
            <div class="vrow-input">
              <el-input-number
                :model-value="v.sRef.value ?? undefined"
                @update:model-value="val => v.sRef.value = val ?? null"
                :min="0" :max="400" :step="1" :precision="1"
                placeholder="实测强度"
                style="width: 160px"
              />
              <span class="unit-s">MPa</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 强度分析与推荐 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><TrendCharts /></el-icon>
        强度分析与推荐
      </div>
      <div class="cs-section-body">
        <el-row :gutter="20" style="margin-bottom: 16px">
          <el-col :span="12">
            <table class="sum-tbl">
              <thead><tr><th>水胶比 W/B</th><th>抗压强度（MPa）</th></tr></thead>
              <tbody>
                <tr>
                  <td>{{ wb.toFixed(3) }}（基准）</td>
                  <td>{{ sWb0 !== null ? fmt(sWb0) : '—' }}</td>
                </tr>
                <tr>
                  <td>{{ (wb + 0.01).toFixed(3) }}</td>
                  <td>{{ sWbPlus !== null ? fmt(sWbPlus) : '—' }}</td>
                </tr>
                <tr>
                  <td>{{ (wb - 0.01).toFixed(3) }}</td>
                  <td>{{ sWbMinus !== null ? fmt(sWbMinus) : '—' }}</td>
                </tr>
              </tbody>
            </table>
          </el-col>
          <el-col :span="12">
            <table class="sum-tbl">
              <thead><tr><th>硅灰用量（kg）</th><th>抗压强度（MPa）</th></tr></thead>
              <tbody>
                <tr>
                  <td>{{ trialMix ? fmt(trialMix.silica_fume) : '—' }}（基准）</td>
                  <td>{{ sWb0 !== null ? fmt(sWb0) : '—' }}</td>
                </tr>
                <tr>
                  <td>{{ vSfPlus ? fmt(vSfPlus.silica_fume) : '—' }}</td>
                  <td>{{ sSfPlus !== null ? fmt(sSfPlus) : '—' }}</td>
                </tr>
                <tr>
                  <td>{{ vSfMinus ? fmt(vSfMinus.silica_fume) : '—' }}</td>
                  <td>{{ sSfMinus !== null ? fmt(sSfMinus) : '—' }}</td>
                </tr>
              </tbody>
            </table>
          </el-col>
        </el-row>
        <div class="rec-row">
          <div class="rec-card">
            <div class="rec-card__label">推荐水胶比</div>
            <div class="rec-card__val">{{ recWb !== null ? recWb.toFixed(3) : '—' }}</div>
            <div class="rec-card__sub">三点线性回归</div>
          </div>
          <div class="rec-card">
            <div class="rec-card__label">推荐硅灰用量</div>
            <div class="rec-card__val">{{ recSf !== null ? recSf.toFixed(1) + ' kg' : '—' }}</div>
            <div class="rec-card__sub">三点线性回归</div>
          </div>
          <div class="rec-card rec-card--target">
            <div class="rec-card__label">配制强度目标</div>
            <div class="rec-card__val">{{ designStr.toFixed(1) }} MPa</div>
            <div class="rec-card__sub">UC{{ strengthGrade }} × 1.10</div>
          </div>
        </div>
        <el-alert type="info" :closable="false" style="margin-top: 14px">
          <b>说明：</b>基于基准、+0.01、−0.01 三点对水胶比与强度进行最小二乘线性回归；
          基于基准、+5%、−5% 三点对硅灰用量与强度进行最小二乘线性回归。
          选择比配制强度（{{ fmt(designStr) }} MPa）略高的参数组合，优先考虑水胶比调整。
        </el-alert>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pane-lead { margin: 0 0 20px; font-size: 13px; color: #6b7280; line-height: 1.75; }

/* ── Variant list ─────────────────────────────────────────────── */
.variant-row { display: flex; align-items: center; gap: 10px; background: #fafbff; border: 1px solid #e5e9f2; border-radius: 10px; padding: 8px 12px; }
.vrow-tag { width: 84px; flex-shrink: 0; font-size: 12px; font-weight: 800; text-align: center; padding: 5px 6px; border-radius: 6px; line-height: 1.3; display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 2px; }
.tag--wb { background: #dbeafe; color: #1d4ed8; }
.tag--sf { background: #fef3c7; color: #92400e; }
.tag--base { background: #d1e7dd; color: #0f5132; width: auto; min-width: 84px; }
.tag-extra { font-size: 10px; font-weight: 400; opacity: 0.75; line-height: 1.5; }
.variant-row--base { border-color: #a3d0b8; background: #f6fdf8; }
.vrow-mix { flex: 1; min-width: 0; }
.vrow-input { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.unit-s { font-size: 12px; color: #9ca3af; }
.mix-cell--total { background: #f0f4fa; }
.mix-cell--total .mix-cell__head { color: #1e3c72; }
.mix-cell--total .mix-cell__val { color: #1e3c72; font-weight: 800; }
.sum-tbl { width: 100%; border-collapse: collapse; font-size: 13px; border: 1px solid #e5e9f2; border-radius: 10px; overflow: hidden; }
.sum-tbl thead tr { background: #f0f4fa; }
.sum-tbl th { font-weight: 700; padding: 8px 14px; text-align: center; color: #374151; border-bottom: 1px solid #e5e9f2; }
.sum-tbl td { text-align: center; padding: 8px 14px; border-bottom: 1px solid #f3f4f6; font-weight: 600; color: #374151; }
.sum-tbl tbody tr:last-child td { border-bottom: none; }
.rec-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 16px; }
.rec-card { padding: 14px 16px; border-radius: 12px; background: linear-gradient(135deg, #fff8e8, #fff2d4); border: 1px solid #f5c842; text-align: center; }
.rec-card--target { background: linear-gradient(135deg, #f0f5ff, #dce8ff); border-color: #94b4e0; }
.rec-card__label { font-size: 12px; color: #7a4300; margin-bottom: 6px; font-weight: 600; }
.rec-card--target .rec-card__label { color: #1e3c72; }
.rec-card__val { font-size: 20px; font-weight: 900; color: #b06000; }
.rec-card--target .rec-card__val { color: #1e3c72; }
.rec-card__sub { font-size: 11px; color: #9ca3af; margin-top: 4px; }
</style>
